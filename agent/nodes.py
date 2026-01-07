"""
LangGraph node implementations.
Each node is a discrete step in the agent pipeline.
"""

from typing import Dict, Any
from datetime import datetime, timezone

from agent.state import AgentState
from agent.decision_engine import DecisionEngine, Decision
from memory import FactualMemory, ConversationMemory, SemanticMemory
from rag import RAGRetriever, EvidenceReranker
from tools import CRMTool, CalendarTool, EmailTool
from integrations import get_llm_provider
from observability import trace_logger
from config import settings


# Initialize singletons
factual_memory = FactualMemory()
conversation_memory = ConversationMemory()
knowledge_base = SemanticMemory(collection_name="knowledge_base")

decision_engine = DecisionEngine()
rag_retriever = RAGRetriever(knowledge_base)
reranker = EvidenceReranker()

crm_tool = CRMTool()
calendar_tool = CalendarTool()
email_tool = EmailTool()

llm_provider = get_llm_provider()


def intake_webhook(state: AgentState) -> AgentState:
    """
    Node 1: Intake webhook - entry point for new lead message.
    """
    trace_logger.agent_run_started(
        lead_id=state["lead_id"],
        message=state["query"],
        source=state["source"]
    )

    return state


def load_lead_context(state: AgentState) -> AgentState:
    """
    Node 2: Load lead context from CRM and conversation history.
    """
    # Get or create lead
    lead = factual_memory.get_lead_by_email(state["lead_email"])

    if not lead:
        # Create new lead
        lead = factual_memory.create_lead(
            email=state["lead_email"],
            source=state["source"]
        )

    # Load conversation history
    interactions = factual_memory.get_lead_interactions(lead.id, limit=10)
    conversation_history = [
        {
            "role": inter.message_from,
            "content": inter.message_text
        }
        for inter in reversed(interactions)  # Chronological order
    ]

    state["lead_id"] = lead.id
    state["lead_context"] = lead.to_dict()
    state["conversation_history"] = conversation_history

    return state


def decide_action(state: AgentState) -> AgentState:
    """
    Node 3: Autonomous decision-making.

    This is the CORE AUTONOMY NODE - decides what to do next.
    """
    decision_output = decision_engine.decide(
        query=state["query"],
        conversation_history=state["conversation_history"],
        lead_context=state["lead_context"],
        retrieved_sources=state.get("retrieved_sources")
    )

    state["decision"] = decision_output.decision
    state["decision_reasoning"] = decision_output.reasoning
    state["confidence"] = decision_output.confidence
    state["retrieval_needed"] = decision_output.retrieval_needed
    state["tools_to_use"] = decision_output.required_tools

    # Check if escalation needed
    if decision_output.decision == Decision.ESCALATE:
        state["escalated"] = True
        state["escalation_reason"] = decision_output.escalation_reason

    return state


def retrieve_rag(state: AgentState) -> AgentState:
    """
    Node 4: RAG retrieval (conditional - only if decision says RETRIEVE).
    """
    if not state.get("retrieval_needed", False):
        return state

    # Retrieve relevant chunks
    evidence_list = rag_retriever.retrieve(
        query=state["query"],
        top_k=settings.rag_top_k
    )

    # Re-rank
    reranked = reranker.rerank(evidence_list)

    # Filter low quality
    filtered = reranker.filter_low_quality(
        reranked,
        threshold=settings.rag_confidence_threshold
    )

    # Check for conflicts
    conflict_detected = reranker.detect_conflicts(filtered)

    # Update state
    state["retrieved_sources"] = [e.to_dict() for e in evidence_list]
    state["reranked_sources"] = [e.to_dict() for e in filtered]

    # Adjust confidence if conflicts detected
    if conflict_detected:
        state["confidence"] *= 0.7
        trace_logger.warning(
            "Conflicting sources detected",
            lead_id=state["lead_id"]
        )

    return state


def compose_response(state: AgentState) -> AgentState:
    """
    Node 5: Compose response using LLM.

    Response is grounded in retrieved evidence when available.
    """
    # Build prompt with evidence
    sources_text = ""
    if state.get("reranked_sources"):
        sources_text = "\n\n".join([
            f"[Source: {s['doc_title']}]\n{s['chunk_text']}"
            for s in state["reranked_sources"][:3]
        ])

    conversation_text = "\n".join([
        f"{msg['role']}: {msg['content']}"
        for msg in state["conversation_history"][-3:]
    ])

    system_prompt = """You are a professional sales and operations AI agent for a service business.
Your goal is to help prospects by providing accurate information and moving them through the sales funnel.

Guidelines:
- Be professional but friendly
- Ground your answers in the provided sources
- If sources are insufficient, ask clarifying questions
- Proactively suggest next steps (book a call, request demo, etc.)
- Keep responses concise (2-3 paragraphs max)
"""

    prompt = f"""CONVERSATION HISTORY:
{conversation_text}

CURRENT QUERY:
{state['query']}

RETRIEVED INFORMATION:
{sources_text if sources_text else "No specific sources retrieved - use general knowledge about sales process."}

LEAD CONTEXT:
- Status: {state['lead_context'].get('status', 'new')}
- Company: {state['lead_context'].get('company', 'unknown')}

Compose a helpful response to the current query."""

    try:
        response_text = llm_provider.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=500
        )

        state["response_text"] = response_text
        state["grounded"] = bool(sources_text)
        state["sources_used"] = [
            s["doc_title"] for s in state.get("reranked_sources", [])[:3]
        ]

        trace_logger.response_composed(
            response_text=response_text,
            grounded=state["grounded"],
            sources_used=state["sources_used"]
        )

        # Enforce confidence thresholds
        should_escalate_flag, escalation_reason = decision_engine.should_escalate(
            confidence=state.get("confidence", 0.0),
            error_occurred=False,
            sensitive_topic=False  # Could add detection logic here
        )

        if should_escalate_flag and not state.get("escalated"):
            state["escalated"] = True
            state["escalation_reason"] = escalation_reason
            trace_logger.warning(
                f"Confidence below threshold, escalating",
                confidence=state.get("confidence"),
                reason=escalation_reason
            )

    except Exception as e:
        trace_logger.error_occurred(
            error_type="response_composition_error",
            error_message=str(e)
        )
        state["errors"].append(f"Response composition failed: {str(e)}")
        state["response_text"] = "I apologize, but I'm having trouble formulating a response. A team member will reach out to you shortly."
        state["escalated"] = True
        state["escalation_reason"] = "response_generation_error"

    return state


def execute_tools(state: AgentState) -> AgentState:
    """
    Node 6: Execute tools (CRM, Calendar, Email) with error handling.
    """
    if not state.get("tools_to_use"):
        return state

    tool_results = []
    tool_errors = []

    for tool_name in state["tools_to_use"]:
        try:
            # Determine tool and action
            if "crm" in tool_name.lower():
                result = _execute_crm_tool(state)
            elif "calendar" in tool_name.lower():
                result = _execute_calendar_tool(state)
            elif "email" in tool_name.lower():
                result = _execute_email_tool(state)
            else:
                result = {"success": False, "error": f"Unknown tool: {tool_name}"}

            tool_results.append(result)

            if not result.get("success"):
                tool_errors.append(f"{tool_name}: {result.get('error')}")

        except Exception as e:
            error_msg = f"Tool execution failed: {str(e)}"
            tool_errors.append(error_msg)
            trace_logger.error_occurred(
                error_type="tool_execution_error",
                error_message=error_msg,
                context={"tool": tool_name}
            )

    state["tool_results"] = tool_results
    state["tool_errors"] = tool_errors

    # If critical tools failed, escalate
    if tool_errors and "calendar" in str(tool_errors):
        state["escalated"] = True
        state["escalation_reason"] = "tool_failure"

    return state


def _execute_crm_tool(state: AgentState) -> Dict[str, Any]:
    """Execute CRM tool operations."""
    # Upsert lead with latest info
    result = crm_tool.execute_with_retry(
        action="upsert",
        email=state["lead_email"],
        name=state["lead_context"].get("name"),
        source=state["source"]
    )

    # Update status to contacted
    if result.success:
        crm_tool.execute(
            action="update_status",
            lead_id=state["lead_id"],
            status="contacted"
        )

    return result.to_dict()


def _execute_calendar_tool(state: AgentState) -> Dict[str, Any]:
    """Execute calendar tool operations."""
    # Only book if query indicates interest
    query_lower = state["query"].lower()
    if "call" in query_lower or "meeting" in query_lower or "schedule" in query_lower:
        result = calendar_tool.execute_with_retry(
            action="book_meeting",
            lead_email=state["lead_email"],
            lead_name=state["lead_context"].get("name"),
            meeting_type="discovery_call"
        )
        return result.to_dict()

    return {"success": True, "message": "No meeting booking needed"}


def _execute_email_tool(state: AgentState) -> Dict[str, Any]:
    """Execute email tool operations."""
    # Send follow-up if appropriate
    result = email_tool.execute_with_retry(
        action="send",
        to_email=state["lead_email"],
        subject=f"Re: Your inquiry",
        body=state["response_text"]
    )
    return result.to_dict()


def update_memory(state: AgentState) -> AgentState:
    """
    Node 7: Update both factual and semantic memory.
    """
    # Add interaction to factual memory
    factual_memory.add_interaction(
        lead_id=state["lead_id"],
        message_from="lead",
        message_text=state["query"],
        decision_type=state.get("decision"),
        confidence_score=state.get("confidence"),
        tools_used=state.get("tools_to_use", []),
        sources_retrieved=state.get("sources_used", [])
    )

    factual_memory.add_interaction(
        lead_id=state["lead_id"],
        message_from="agent",
        message_text=state.get("response_text", ""),
        decision_type=state.get("decision"),
        confidence_score=state.get("confidence")
    )

    # Add to semantic memory (conversation history)
    conversation_memory.add_conversation_turn(
        lead_id=state["lead_id"],
        role="user",
        message=state["query"]
    )

    conversation_memory.add_conversation_turn(
        lead_id=state["lead_id"],
        role="agent",
        message=state.get("response_text", "")
    )

    trace_logger.memory_updated(
        memory_type="both",
        lead_id=state["lead_id"],
        operation="add_interaction"
    )

    return state


def handle_escalation(state: AgentState) -> AgentState:
    """
    Node 8: Handle escalation to human.
    """
    if not state.get("escalated"):
        return state

    # Create escalation event
    factual_memory.create_escalation(
        lead_id=state["lead_id"],
        reason=state.get("escalation_reason", "unknown"),
        confidence_score=state.get("confidence", 0.0),
        context={
            "query": state["query"],
            "decision": state.get("decision"),
            "errors": state.get("errors", [])
        }
    )

    # Update lead status
    crm_tool.execute(
        action="update_status",
        lead_id=state["lead_id"],
        status="escalated"
    )

    # Modify response to indicate escalation
    state["response_text"] = (
        "Thank you for your inquiry. I want to ensure you get the best possible assistance, "
        "so I'm connecting you with one of our team members who will follow up with you shortly."
    )

    trace_logger.info(
        "Escalation handled",
        lead_id=state["lead_id"],
        reason=state.get("escalation_reason")
    )

    return state


def finalize(state: AgentState) -> AgentState:
    """
    Node 9: Finalize and return results.
    """
    trace_logger.agent_run_completed(
        lead_id=state["lead_id"],
        success=not state.get("escalated", False),
        duration_ms=0  # Would calculate actual duration
    )

    return state
