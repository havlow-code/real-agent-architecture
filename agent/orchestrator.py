"""
LangGraph orchestrator - connects all nodes into autonomous agent pipeline.
"""

from langgraph.graph import StateGraph, END
from typing import Dict, Any

from agent.state import AgentState
from agent.nodes import (
    intake_webhook,
    load_lead_context,
    decide_action,
    retrieve_rag,
    compose_response,
    execute_tools,
    update_memory,
    handle_escalation,
    finalize
)
from agent.decision_engine import Decision
from observability import trace_logger


def should_retrieve(state: AgentState) -> str:
    """Conditional edge: decide if RAG retrieval is needed."""
    if state.get("retrieval_needed"):
        return "retrieve"
    return "compose"


def should_use_tools(state: AgentState) -> str:
    """Conditional edge: decide if tools should be executed."""
    if state.get("tools_to_use"):
        return "tools"
    return "memory"


def should_escalate(state: AgentState) -> str:
    """Conditional edge: decide if escalation is needed."""
    if state.get("escalated"):
        return "escalate"
    return "memory"


class AgentOrchestrator:
    """
    Orchestrates the autonomous agent using LangGraph.

    Graph structure:
    1. intake_webhook -> load_lead_context
    2. load_lead_context -> decide_action
    3. decide_action -> [retrieve_rag OR compose_response]
    4. retrieve_rag -> compose_response
    5. compose_response -> [escalate OR execute_tools OR update_memory]
    6. execute_tools -> update_memory
    7. handle_escalation -> update_memory
    8. update_memory -> finalize
    9. finalize -> END
    """

    def __init__(self):
        self.graph = self._build_graph()
        self.compiled_graph = self.graph.compile()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state machine."""
        # Create graph
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("intake", intake_webhook)
        workflow.add_node("load_context", load_lead_context)
        workflow.add_node("decide", decide_action)
        workflow.add_node("retrieve", retrieve_rag)
        workflow.add_node("compose", compose_response)
        workflow.add_node("tools", execute_tools)
        workflow.add_node("escalate", handle_escalation)
        workflow.add_node("memory", update_memory)
        workflow.add_node("finalize", finalize)

        # Set entry point
        workflow.set_entry_point("intake")

        # Add edges
        workflow.add_edge("intake", "load_context")
        workflow.add_edge("load_context", "decide")

        # Conditional: retrieve or compose
        workflow.add_conditional_edges(
            "decide",
            should_retrieve,
            {
                "retrieve": "retrieve",
                "compose": "compose"
            }
        )

        workflow.add_edge("retrieve", "compose")

        # Conditional: escalate, tools, or memory
        workflow.add_conditional_edges(
            "compose",
            should_escalate,
            {
                "escalate": "escalate",
                "memory": "memory"  # Skip tools if escalating
            }
        )

        # If not escalating, check for tools
        # NOTE: In production, this would be a more complex conditional
        # For PoC, we have a simple check in should_use_tools

        workflow.add_edge("tools", "memory")
        workflow.add_edge("escalate", "memory")
        workflow.add_edge("memory", "finalize")
        workflow.add_edge("finalize", END)

        return workflow

    def run(
        self,
        lead_email: str,
        query: str,
        source: str = "website_form",
        trace_id: str = None
    ) -> Dict[str, Any]:
        """
        Run the agent pipeline.

        Args:
            lead_email: Lead email address
            query: User query/message
            source: Source of the inquiry
            trace_id: Optional trace ID for logging

        Returns:
            Final state dictionary
        """
        # Initialize state
        initial_state: AgentState = {
            "lead_id": "",  # Will be populated
            "lead_email": lead_email,
            "query": query,
            "source": source,
            "lead_context": {},
            "conversation_history": [],
            "decision": None,
            "decision_reasoning": "",
            "confidence": 0.0,
            "retrieval_needed": False,
            "retrieved_sources": [],
            "reranked_sources": [],
            "response_text": "",
            "sources_used": [],
            "grounded": False,
            "tools_to_use": [],
            "tool_results": [],
            "tool_errors": [],
            "escalated": False,
            "escalation_reason": None,
            "trace_id": trace_id or trace_logger.generate_trace_id(),
            "next_action": None,
            "errors": []
        }

        # Run graph with tracing
        with trace_logger.trace(initial_state["trace_id"]):
            try:
                final_state = self.compiled_graph.invoke(initial_state)
                return final_state
            except Exception as e:
                trace_logger.error_occurred(
                    error_type="agent_orchestration_error",
                    error_message=str(e),
                    context={"lead_email": lead_email, "query": query}
                )
                # Return error state
                return {
                    **initial_state,
                    "escalated": True,
                    "escalation_reason": "orchestration_error",
                    "errors": [str(e)],
                    "response_text": "I apologize, but I'm experiencing technical difficulties. A team member will assist you shortly."
                }


# Singleton instance
agent_orchestrator = AgentOrchestrator()
