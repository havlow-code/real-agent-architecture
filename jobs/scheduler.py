"""
Background job scheduler for follow-ups and maintenance tasks.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timezone

from memory import FactualMemory
from tools import EmailTool
from config import settings
from observability import trace_logger


class JobScheduler:
    """Background job scheduler."""

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.factual_memory = FactualMemory()
        self.email_tool = EmailTool()

    def start(self):
        """Start the scheduler."""
        if not settings.enable_background_jobs:
            trace_logger.info("Background jobs disabled")
            return

        # Add jobs
        self.scheduler.add_job(
            func=self.check_followups,
            trigger=IntervalTrigger(
                minutes=settings.followup_check_interval_minutes
            ),
            id="check_followups",
            name="Check and send follow-ups",
            replace_existing=True
        )

        self.scheduler.start()
        trace_logger.info("Job scheduler started")

    def stop(self):
        """Stop the scheduler."""
        self.scheduler.shutdown()
        trace_logger.info("Job scheduler stopped")

    def check_followups(self):
        """Check for leads that need follow-up."""
        try:
            leads = self.factual_memory.get_leads_for_followup()

            trace_logger.info(
                f"Checking follow-ups",
                num_leads=len(leads)
            )

            for lead in leads:
                self._send_followup(lead)

        except Exception as e:
            trace_logger.error_occurred(
                error_type="followup_check_error",
                error_message=str(e)
            )

    def _send_followup(self, lead):
        """Send follow-up email to lead."""
        try:
            result = self.email_tool.execute(
                action="send_followup",
                to_email=lead.email,
                lead_name=lead.name,
                context=f"You were interested in learning more about our services."
            )

            if result.success:
                # Update last contacted
                from datetime import timedelta
                self.factual_memory.update_lead(
                    lead.id,
                    last_contacted_at=datetime.now(timezone.utc),
                    next_followup_at=datetime.now(timezone.utc) + timedelta(days=7)
                )

                trace_logger.info(
                    "Follow-up sent",
                    lead_id=lead.id,
                    email=lead.email
                )

        except Exception as e:
            trace_logger.error_occurred(
                error_type="followup_send_error",
                error_message=str(e),
                context={"lead_id": lead.id}
            )


# Singleton instance
job_scheduler = JobScheduler()
