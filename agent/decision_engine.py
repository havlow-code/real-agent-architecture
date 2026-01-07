"""
Decision engine with autonomous decision-making and confidence scoring.
This is the CORE autonomy implementation.

The agent explicitly decides:
- RETRIEVE: needs factual lookup from knowledge base
- REASON_ONLY: can answer from existing context
- USE_TOOL: requires tool execution
- CLARIFY: needs clarification from user
- ESCALATE: beyond agent capability or low confidence
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from models.schemas import DecisionType, ConfidenceFactors
from integrations import get_llm_provider
from observability import trace_logger
from config import settings


class Decision(str, Enum):
    """Agent decision types."""
    RETRIEVE = "retrieve"
    REASON_ONLY = "reason_only"
    USE_TOOL = "use_tool"
    CLARIFY = "clarify"
    ESCALATE = "escalate"


@dataclass
class DecisionOutput:
    """Output from decision engine."""
    decision: Decision
    confidence: float
    reasoning: str
    required_tools: List[str]
    retrieval_needed: bool
    escalation_reason: Optional[str] = None


class DecisionEngine:
    """
    Autonomous decision engine.

    This is NOT a rule-based system - it uses LLM reasoning to decide
    what action to take based on the current state.
    """

    def __init__(self):
        self.llm = get_llm_provider()
        self.high_threshold = settings.confidence_high_threshold
        self.low_threshold = settings.confidence_low_threshold

    def decide(
        self,
        query: str,
        conversation_history: List[Dict[str, str]],
        lead_context: Dict[str, Any],
        retrieved_sources: List[Any] = None
    ) -> DecisionOutput:
        """
        Make autonomous decision about next action.

        This is the CORE AUTONOMY FEATURE.

        Args:
            query: Current user query
            conversation_history: Recent conversation
            lead_context: Lead information from CRM
            retrieved_sources: Previously retrieved sources (if any)

        Returns:
            DecisionOutput with decision and reasoning
        """
        # Build decision prompt
        decision_prompt = self._build_decision_prompt(
            query=query,
            conversation_history=conversation_history,
            lead_context=lead_context,
            retrieved_sources=retrieved_sources
        )

        # Get LLM decision
        try:
            response = self.llm.generate(
                prompt=decision_prompt,
                system_prompt="You are an autonomous agent decision engine. Analyze the situation and decide the best action.",
                temperature=0.3,  # Lower temperature for consistent decisions
                max_tokens=500
            )

            # Parse decision from response
            decision_output = self._parse_decision(response)

            # Log decision
            trace_logger.decision_made(
                decision=decision_output.decision.value,
                confidence=decision_output.confidence,
                reasoning=decision_output.reasoning,
                required_tools=decision_output.required_tools,
                retrieval_needed=decision_output.retrieval_needed
            )

            return decision_output

        except Exception as e:
            trace_logger.error_occurred(
                error_type="decision_engine_error",
                error_message=str(e)
            )

            # Fallback: escalate on error
            return DecisionOutput(
                decision=Decision.ESCALATE,
                confidence=0.0,
                reasoning=f"Decision engine error: {str(e)}",
                required_tools=[],
                retrieval_needed=False,
                escalation_reason="internal_error"
            )

    def _build_decision_prompt(
        self,
        query: str,
        conversation_history: List[Dict[str, str]],
        lead_context: Dict[str, Any],
        retrieved_sources: List[Any]
    ) -> str:
        """Build prompt for decision-making."""
        history_text = "\n".join([
            f"{msg.get('role', 'unknown')}: {msg.get('content', '')}"
            for msg in conversation_history[-5:]
        ])

        sources_text = "None"
        if retrieved_sources:
            sources_text = f"{len(retrieved_sources)} sources available"

        prompt = f"""You are an autonomous AI agent for a service business. Analyze this situation and decide the best action.

CURRENT QUERY:
{query}

RECENT CONVERSATION:
{history_text}

LEAD CONTEXT:
- Email: {lead_context.get('email', 'unknown')}
- Name: {lead_context.get('name', 'unknown')}
- Status: {lead_context.get('status', 'new')}
- Company: {lead_context.get('company', 'unknown')}

PREVIOUSLY RETRIEVED SOURCES:
{sources_text}

AVAILABLE ACTIONS:
1. RETRIEVE - Query knowledge base for factual information (pricing, policies, SOPs, FAQs)
2. REASON_ONLY - Answer using existing context (no retrieval needed)
3. USE_TOOL - Execute tools (CRM update, book meeting, send email)
4. CLARIFY - Ask user for more information
5. ESCALATE - Pass to human (complex, sensitive, or low confidence)

DECISION CRITERIA:
- Use RETRIEVE if query asks about: pricing, policies, procedures, technical details
- Use REASON_ONLY if: simple acknowledgment, already have info, conversational
- Use USE_TOOL if: need to update CRM, book meeting, send email
- Use CLARIFY if: query is ambiguous, missing key information
- Use ESCALATE if: sensitive issue, legal question, complaint, beyond capability

Respond in this EXACT format:
DECISION: [one of: RETRIEVE, REASON_ONLY, USE_TOOL, CLARIFY, ESCALATE]
CONFIDENCE: [0.0 to 1.0]
REASONING: [one sentence explaining why]
TOOLS_NEEDED: [comma-separated list or "none"]
RETRIEVAL_NEEDED: [yes or no]
"""

        return prompt

    def _parse_decision(self, response: str) -> DecisionOutput:
        """Parse LLM decision response."""
        lines = response.strip().split("\n")
        parsed = {}

        for line in lines:
            if ":" in line:
                key, value = line.split(":", 1)
                parsed[key.strip().upper()] = value.strip()

        # Extract decision
        decision_str = parsed.get("DECISION", "ESCALATE")
        decision_map = {
            "RETRIEVE": Decision.RETRIEVE,
            "REASON_ONLY": Decision.REASON_ONLY,
            "USE_TOOL": Decision.USE_TOOL,
            "CLARIFY": Decision.CLARIFY,
            "ESCALATE": Decision.ESCALATE
        }
        decision = decision_map.get(decision_str, Decision.ESCALATE)

        # Extract confidence
        try:
            confidence = float(parsed.get("CONFIDENCE", "0.5"))
            confidence = max(0.0, min(1.0, confidence))
        except ValueError:
            confidence = 0.5

        # Extract reasoning
        reasoning = parsed.get("REASONING", "No reasoning provided")

        # Extract tools
        tools_str = parsed.get("TOOLS_NEEDED", "none")
        required_tools = []
        if tools_str.lower() != "none":
            required_tools = [t.strip() for t in tools_str.split(",")]

        # Extract retrieval flag
        retrieval_needed = parsed.get("RETRIEVAL_NEEDED", "no").lower() == "yes"

        return DecisionOutput(
            decision=decision,
            confidence=confidence,
            reasoning=reasoning,
            required_tools=required_tools,
            retrieval_needed=retrieval_needed
        )

    def calculate_confidence(
        self,
        sources_quality: float,
        query_complexity: float,
        context_completeness: float,
        tool_success_rate: float,
        conflict_detected: bool
    ) -> float:
        """
        Calculate composite confidence score.

        Factors:
        - source_quality: Quality of retrieved sources (0-1)
        - query_complexity: How complex is the query (0=simple, 1=complex)
        - context_completeness: How complete is our context (0-1)
        - tool_success_rate: Success rate of tool calls (0-1)
        - conflict_detected: Whether conflicting information exists

        Args:
            sources_quality: Quality of sources
            query_complexity: Query complexity
            context_completeness: Context completeness
            tool_success_rate: Tool success rate
            conflict_detected: Conflict flag

        Returns:
            Confidence score (0-1)
        """
        # Base confidence from factors
        base_confidence = (
            0.3 * sources_quality +
            0.2 * (1.0 - query_complexity) +  # Lower complexity = higher confidence
            0.3 * context_completeness +
            0.2 * tool_success_rate
        )

        # Penalty for conflicts
        if conflict_detected:
            base_confidence *= 0.5

        # Clamp to [0, 1]
        confidence = max(0.0, min(1.0, base_confidence))

        # Log confidence calculation
        trace_logger.confidence_calculated(
            confidence=confidence,
            factors={
                "sources_quality": sources_quality,
                "query_complexity": query_complexity,
                "context_completeness": context_completeness,
                "tool_success_rate": tool_success_rate,
                "conflict_detected": conflict_detected
            },
            threshold_met=confidence >= self.high_threshold
        )

        return confidence

    def should_escalate(
        self,
        confidence: float,
        error_occurred: bool = False,
        sensitive_topic: bool = False
    ) -> tuple[bool, Optional[str]]:
        """
        Determine if escalation is needed.

        Args:
            confidence: Current confidence score
            error_occurred: Whether an error occurred
            sensitive_topic: Whether topic is sensitive

        Returns:
            Tuple of (should_escalate, reason)
        """
        if error_occurred:
            return True, "error_in_processing"

        if sensitive_topic:
            return True, "sensitive_topic_detected"

        if confidence < self.low_threshold:
            return True, "confidence_below_threshold"

        return False, None
