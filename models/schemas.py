"""
Pydantic schemas for API requests and responses.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum


class DecisionType(str, Enum):
    """Agent decision types."""
    RETRIEVE = "retrieve"
    REASON_ONLY = "reason_only"
    USE_TOOL = "use_tool"
    CLARIFY = "clarify"
    ESCALATE = "escalate"


class LeadWebhookRequest(BaseModel):
    """Incoming webhook request for new lead."""
    email: EmailStr = Field(..., description="Lead email address")
    name: Optional[str] = Field(None, description="Lead name")
    message: str = Field(..., description="Lead message/query")
    source: str = Field(default="website_form", description="Lead source")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class LeadStatusResponse(BaseModel):
    """Response with lead status and history."""
    lead_id: str
    email: str
    name: Optional[str]
    company: Optional[str]
    status: str
    qualification_score: float
    created_at: datetime
    last_contacted_at: Optional[datetime]
    next_followup_at: Optional[datetime]
    recent_interactions: List[Dict[str, Any]]


class AgentResponse(BaseModel):
    """Agent response to lead query."""
    response_text: str = Field(..., description="Agent response")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    decision_type: DecisionType = Field(..., description="Decision made by agent")
    sources_used: List[str] = Field(default_factory=list, description="Sources cited")
    tools_called: List[str] = Field(default_factory=list, description="Tools invoked")
    escalated: bool = Field(default=False, description="Whether escalated to human")
    next_action: Optional[str] = Field(None, description="Recommended next action")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(default="healthy")
    timestamp: datetime = Field(default_factory=lambda: datetime.utcnow())
    version: str = Field(default="1.0.0")


class ToolResult(BaseModel):
    """Result from tool execution."""
    success: bool = Field(..., description="Whether tool succeeded")
    data: Optional[Dict[str, Any]] = Field(None, description="Result data")
    error: Optional[str] = Field(None, description="Error message if failed")
    retry_allowed: bool = Field(default=False, description="Whether retry is allowed")


class Evidence(BaseModel):
    """Evidence from RAG retrieval."""
    source_id: str = Field(..., description="Source document ID")
    doc_title: str = Field(..., description="Document title")
    chunk_text: str = Field(..., description="Retrieved chunk text")
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata")


class ConfidenceFactors(BaseModel):
    """Factors contributing to confidence score."""
    source_quality: float = Field(..., ge=0.0, le=1.0)
    query_complexity: float = Field(..., ge=0.0, le=1.0)
    context_completeness: float = Field(..., ge=0.0, le=1.0)
    tool_success_rate: float = Field(..., ge=0.0, le=1.0)
    conflict_detected: bool = Field(default=False)
