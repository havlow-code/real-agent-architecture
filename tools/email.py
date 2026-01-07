"""
Email tool for sending messages.
Mock implementation logging emails.
In production, would integrate with SendGrid, SMTP, etc.
"""

from typing import Optional, List
from datetime import datetime, timezone
import uuid

from tools.base import Tool, ToolResult
from observability import trace_logger


class EmailTool(Tool):
    """Email sending tool."""

    def __init__(self):
        super().__init__(name="email_tool")
        # Store sent emails (for testing/verification)
        self.sent_emails = []

    def execute(self, action: str, **kwargs) -> ToolResult:
        """
        Execute email action.

        Args:
            action: Action to perform (send, send_followup)
            **kwargs: Action-specific parameters

        Returns:
            ToolResult with operation outcome
        """
        actions = {
            "send": self._send_email,
            "send_followup": self._send_followup
        }

        handler = actions.get(action)
        if not handler:
            return ToolResult(
                success=False,
                error=f"Unknown email action: {action}",
                retry_allowed=False
            )

        try:
            return handler(**kwargs)
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Email operation failed: {str(e)}",
                retry_allowed=True  # API calls can be retried
            )

    def _send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        from_email: Optional[str] = None,
        cc: Optional[List[str]] = None
    ) -> ToolResult:
        """
        Send an email.

        Args:
            to_email: Recipient email
            subject: Email subject
            body: Email body
            from_email: Sender email (optional)
            cc: CC recipients (optional)

        Returns:
            ToolResult with send status
        """
        # Simulate API call with small chance of transient failure
        import random
        if random.random() < 0.05:
            return ToolResult(
                success=False,
                error="Email service temporarily unavailable",
                retry_allowed=True
            )

        # Create email record
        email_id = str(uuid.uuid4())
        email = {
            "email_id": email_id,
            "to": to_email,
            "from": from_email or "agent@company.com",
            "cc": cc or [],
            "subject": subject,
            "body": body,
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "status": "sent"
        }

        self.sent_emails.append(email)

        trace_logger.info(
            "Email sent successfully",
            email_id=email_id,
            to=to_email,
            subject=subject
        )

        return ToolResult(
            success=True,
            data={
                "email_id": email_id,
                "status": "sent",
                "sent_at": email["sent_at"]
            }
        )

    def _send_followup(
        self,
        to_email: str,
        lead_name: Optional[str] = None,
        context: Optional[str] = None
    ) -> ToolResult:
        """
        Send a follow-up email.

        Uses a template for follow-ups.

        Args:
            to_email: Recipient email
            lead_name: Lead name
            context: Additional context for personalization

        Returns:
            ToolResult with send status
        """
        # Build follow-up email
        name = lead_name or "there"
        subject = f"Following up on your inquiry"

        body = f"""Hi {name},

I wanted to follow up on our previous conversation. {context or "I'm here to help answer any questions you might have."}

Would you be interested in scheduling a brief call to discuss further?

Best regards,
Sales Team
"""

        return self._send_email(
            to_email=to_email,
            subject=subject,
            body=body
        )

    def get_sent_emails(self, to_email: Optional[str] = None) -> List[dict]:
        """
        Get sent emails (for testing/verification).

        Args:
            to_email: Filter by recipient

        Returns:
            List of sent emails
        """
        if to_email:
            return [e for e in self.sent_emails if e["to"] == to_email]
        return self.sent_emails
