"""
Calendar tool for booking meetings.
Mock implementation simulating calendar integration.
In production, would integrate with Google Calendar, Calendly, etc.
"""

from typing import Optional
from datetime import datetime, timezone, timedelta
import uuid

from tools.base import Tool, ToolResult
from observability import trace_logger


class CalendarTool(Tool):
    """Calendar operations tool for meeting scheduling."""

    def __init__(self):
        super().__init__(name="calendar_tool")
        # In production, would initialize calendar API client here
        # For PoC, we simulate bookings in memory
        self.bookings = {}

    def execute(self, action: str, **kwargs) -> ToolResult:
        """
        Execute calendar action.

        Args:
            action: Action to perform (book_meeting, check_availability, cancel_meeting)
            **kwargs: Action-specific parameters

        Returns:
            ToolResult with operation outcome
        """
        actions = {
            "book_meeting": self._book_meeting,
            "check_availability": self._check_availability,
            "cancel_meeting": self._cancel_meeting
        }

        handler = actions.get(action)
        if not handler:
            return ToolResult(
                success=False,
                error=f"Unknown calendar action: {action}",
                retry_allowed=False
            )

        try:
            return handler(**kwargs)
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Calendar operation failed: {str(e)}",
                retry_allowed=True  # API calls can be retried
            )

    def _book_meeting(
        self,
        lead_email: str,
        lead_name: Optional[str] = None,
        meeting_type: str = "discovery_call",
        duration_minutes: int = 30,
        preferred_date: Optional[str] = None
    ) -> ToolResult:
        """
        Book a meeting.

        Args:
            lead_email: Lead email address
            lead_name: Lead name
            meeting_type: Type of meeting
            duration_minutes: Meeting duration
            preferred_date: Preferred date (ISO format) or None for auto-schedule

        Returns:
            ToolResult with booking details
        """
        # Simulate API call delay/failure (10% chance of transient failure)
        import random
        if random.random() < 0.1:
            return ToolResult(
                success=False,
                error="Calendar API temporarily unavailable",
                retry_allowed=True  # Transient failure
            )

        # Generate meeting time
        if preferred_date:
            try:
                meeting_time = datetime.fromisoformat(preferred_date)
            except ValueError:
                return ToolResult(
                    success=False,
                    error=f"Invalid date format: {preferred_date}",
                    retry_allowed=False
                )
        else:
            # Auto-schedule 2 days from now at 10 AM
            meeting_time = datetime.now(timezone.utc) + timedelta(days=2)
            meeting_time = meeting_time.replace(hour=10, minute=0, second=0, microsecond=0)

        # Create booking
        booking_id = str(uuid.uuid4())
        meeting_link = f"https://meet.company.com/{booking_id[:8]}"

        booking = {
            "booking_id": booking_id,
            "lead_email": lead_email,
            "lead_name": lead_name or "Prospect",
            "meeting_type": meeting_type,
            "scheduled_at": meeting_time.isoformat(),
            "duration_minutes": duration_minutes,
            "meeting_link": meeting_link,
            "status": "confirmed"
        }

        self.bookings[booking_id] = booking

        trace_logger.info(
            "Meeting booked successfully",
            booking_id=booking_id,
            lead_email=lead_email,
            scheduled_at=meeting_time.isoformat()
        )

        return ToolResult(
            success=True,
            data=booking
        )

    def _check_availability(
        self,
        date: Optional[str] = None,
        num_days: int = 7
    ) -> ToolResult:
        """
        Check availability.

        In mock implementation, returns available slots.
        In production, would query actual calendar.

        Args:
            date: Starting date (ISO format)
            num_days: Number of days to check

        Returns:
            ToolResult with available slots
        """
        start_date = datetime.now(timezone.utc)
        if date:
            try:
                start_date = datetime.fromisoformat(date)
            except ValueError:
                return ToolResult(
                    success=False,
                    error=f"Invalid date format: {date}",
                    retry_allowed=False
                )

        # Generate mock available slots
        available_slots = []
        for day in range(num_days):
            slot_date = start_date + timedelta(days=day)
            # Skip weekends
            if slot_date.weekday() >= 5:
                continue

            # Mock slots at 10 AM, 2 PM, 4 PM
            for hour in [10, 14, 16]:
                slot_time = slot_date.replace(hour=hour, minute=0, second=0, microsecond=0)
                available_slots.append({
                    "datetime": slot_time.isoformat(),
                    "duration_minutes": 30
                })

        return ToolResult(
            success=True,
            data={
                "available_slots": available_slots[:10],  # Return first 10
                "total_slots": len(available_slots)
            }
        )

    def _cancel_meeting(self, booking_id: str) -> ToolResult:
        """Cancel a meeting."""
        if booking_id not in self.bookings:
            return ToolResult(
                success=False,
                error=f"Booking not found: {booking_id}",
                retry_allowed=False
            )

        booking = self.bookings[booking_id]
        booking["status"] = "cancelled"

        trace_logger.info(
            "Meeting cancelled",
            booking_id=booking_id
        )

        return ToolResult(
            success=True,
            data={"booking_id": booking_id, "status": "cancelled"}
        )
