"""
API routes for agent interactions.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from models.schemas import (
    LeadWebhookRequest, AgentResponse, HealthResponse, LeadStatusResponse
)
from agent import agent_orchestrator
from memory import FactualMemory
from observability import trace_logger


router = APIRouter()
factual_memory = FactualMemory()


@router.post("/webhook/lead", response_model=AgentResponse)
async def webhook_lead(request: LeadWebhookRequest) -> AgentResponse:
    """
    Webhook endpoint for inbound leads.

    This is the main entry point for the agent.
    """
    try:
        # Run agent
        result = agent_orchestrator.run(
            lead_email=request.email,
            query=request.message,
            source=request.source
        )

        # Build response
        response = AgentResponse(
            response_text=result.get("response_text", ""),
            confidence=result.get("confidence", 0.0),
            decision_type=result.get("decision", "escalate"),
            sources_used=result.get("sources_used", []),
            tools_called=[t for t in result.get("tools_to_use", [])],
            escalated=result.get("escalated", False),
            next_action=result.get("next_action")
        )

        return response

    except Exception as e:
        trace_logger.error_occurred(
            error_type="webhook_error",
            error_message=str(e),
            context={"email": request.email}
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent/status/{lead_id}", response_model=LeadStatusResponse)
async def get_lead_status(lead_id: str) -> LeadStatusResponse:
    """Get status and history for a lead."""
    try:
        lead = factual_memory.get_lead_by_id(lead_id)
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")

        # Get recent interactions
        interactions = factual_memory.get_lead_interactions(lead_id, limit=10)

        response = LeadStatusResponse(
            lead_id=lead.id,
            email=lead.email,
            name=lead.name,
            company=lead.company,
            status=lead.status.value if lead.status else "unknown",
            qualification_score=lead.qualification_score or 0.0,
            created_at=lead.created_at,
            last_contacted_at=lead.last_contacted_at,
            next_followup_at=lead.next_followup_at,
            recent_interactions=[i.to_dict() for i in interactions]
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        trace_logger.error_occurred(
            error_type="status_retrieval_error",
            error_message=str(e),
            context={"lead_id": lead_id}
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version="1.0.0"
    )
