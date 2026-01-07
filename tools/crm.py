"""
CRM tool for managing leads and contacts.
Mock implementation using SQLite. Can be swapped with HubSpot/Salesforce in production.
"""

from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta

from tools.base import Tool, ToolResult
from memory import FactualMemory
from models import LeadStatus


class CRMTool(Tool):
    """CRM operations tool."""

    def __init__(self):
        super().__init__(name="crm_tool")
        self.memory = FactualMemory()

    def execute(self, action: str, **kwargs) -> ToolResult:
        """
        Execute CRM action.

        Args:
            action: Action to perform (upsert, qualify, update_status, get_lead)
            **kwargs: Action-specific parameters

        Returns:
            ToolResult with operation outcome
        """
        actions = {
            "upsert": self._upsert_lead,
            "qualify": self._qualify_lead,
            "update_status": self._update_status,
            "get_lead": self._get_lead,
            "schedule_followup": self._schedule_followup
        }

        handler = actions.get(action)
        if not handler:
            return ToolResult(
                success=False,
                error=f"Unknown CRM action: {action}",
                retry_allowed=False
            )

        try:
            return handler(**kwargs)
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"CRM operation failed: {str(e)}",
                retry_allowed=True  # Database operations can be retried
            )

    def _upsert_lead(
        self,
        email: str,
        name: Optional[str] = None,
        company: Optional[str] = None,
        phone: Optional[str] = None,
        source: str = "website_form",
        metadata: Dict[str, Any] = None
    ) -> ToolResult:
        """Create or update a lead."""
        # Check if lead exists
        existing = self.memory.get_lead_by_email(email)

        if existing:
            # Update existing lead
            updates = {}
            if name:
                updates["name"] = name
            if company:
                updates["company"] = company
            if phone:
                updates["phone"] = phone
            if metadata:
                existing_metadata = existing.metadata or {}
                existing_metadata.update(metadata)
                updates["metadata"] = existing_metadata

            lead = self.memory.update_lead(existing.id, **updates)
            action_type = "updated"
        else:
            # Create new lead
            lead = self.memory.create_lead(
                email=email,
                name=name,
                source=source,
                metadata=metadata or {}
            )

            # Update additional fields
            if company or phone:
                updates = {}
                if company:
                    updates["company"] = company
                if phone:
                    updates["phone"] = phone
                lead = self.memory.update_lead(lead.id, **updates)

            action_type = "created"

        return ToolResult(
            success=True,
            data={
                "action": action_type,
                "lead_id": lead.id,
                "email": lead.email,
                "status": lead.status.value if lead.status else None
            }
        )

    def _qualify_lead(
        self,
        lead_id: str,
        budget_range: Optional[str] = None,
        timeline: Optional[str] = None,
        decision_maker: Optional[str] = None,
        qualification_score: Optional[float] = None
    ) -> ToolResult:
        """Qualify a lead with scoring."""
        updates = {}

        if budget_range:
            updates["budget_range"] = budget_range
        if timeline:
            updates["timeline"] = timeline
        if decision_maker:
            updates["decision_maker"] = decision_maker
        if qualification_score is not None:
            updates["qualification_score"] = qualification_score

            # Auto-update status based on score
            if qualification_score >= 0.7:
                updates["status"] = LeadStatus.QUALIFIED
            elif qualification_score < 0.4:
                updates["status"] = LeadStatus.UNQUALIFIED

        lead = self.memory.update_lead(lead_id, **updates)

        if not lead:
            return ToolResult(
                success=False,
                error=f"Lead not found: {lead_id}",
                retry_allowed=False
            )

        return ToolResult(
            success=True,
            data={
                "lead_id": lead.id,
                "qualification_score": lead.qualification_score,
                "status": lead.status.value if lead.status else None
            }
        )

    def _update_status(
        self,
        lead_id: str,
        status: str
    ) -> ToolResult:
        """Update lead status."""
        try:
            lead_status = LeadStatus(status)
        except ValueError:
            return ToolResult(
                success=False,
                error=f"Invalid status: {status}",
                retry_allowed=False
            )

        updates = {
            "status": lead_status,
            "last_contacted_at": datetime.now(timezone.utc)
        }

        lead = self.memory.update_lead(lead_id, **updates)

        if not lead:
            return ToolResult(
                success=False,
                error=f"Lead not found: {lead_id}",
                retry_allowed=False
            )

        return ToolResult(
            success=True,
            data={
                "lead_id": lead.id,
                "status": lead.status.value
            }
        )

    def _get_lead(self, lead_id: str) -> ToolResult:
        """Get lead information."""
        lead = self.memory.get_lead_by_id(lead_id)

        if not lead:
            return ToolResult(
                success=False,
                error=f"Lead not found: {lead_id}",
                retry_allowed=False
            )

        return ToolResult(
            success=True,
            data=lead.to_dict()
        )

    def _schedule_followup(
        self,
        lead_id: str,
        days_from_now: int = 3
    ) -> ToolResult:
        """Schedule a follow-up."""
        followup_time = datetime.now(timezone.utc) + timedelta(days=days_from_now)

        lead = self.memory.update_lead(
            lead_id,
            next_followup_at=followup_time
        )

        if not lead:
            return ToolResult(
                success=False,
                error=f"Lead not found: {lead_id}",
                retry_allowed=False
            )

        return ToolResult(
            success=True,
            data={
                "lead_id": lead.id,
                "followup_scheduled_at": followup_time.isoformat()
            }
        )
