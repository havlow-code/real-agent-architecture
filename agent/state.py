"""
Agent state definition for LangGraph.
Represents all information flowing through the agent pipeline.
"""

from typing import TypedDict, List, Dict, Any, Optional
from models.schemas import DecisionType


class AgentState(TypedDict):
    """State object passed through LangGraph nodes."""

    # Input
    lead_id: str
    lead_email: str
    query: str
    source: str

    # Context
    lead_context: Dict[str, Any]
    conversation_history: List[Dict[str, str]]

    # Decision
    decision: Optional[DecisionType]
    decision_reasoning: str
    confidence: float

    # RAG
    retrieval_needed: bool
    retrieved_sources: List[Dict[str, Any]]
    reranked_sources: List[Dict[str, Any]]

    # Response
    response_text: str
    sources_used: List[str]
    grounded: bool

    # Tools
    tools_to_use: List[str]
    tool_results: List[Dict[str, Any]]
    tool_errors: List[str]

    # Escalation
    escalated: bool
    escalation_reason: Optional[str]

    # Metadata
    trace_id: str
    next_action: Optional[str]
    errors: List[str]
