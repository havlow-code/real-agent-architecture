"""Tool integrations with error handling."""

from tools.base import Tool, ToolResult, TransientError, PermanentError
from tools.crm import CRMTool
from tools.calendar import CalendarTool
from tools.email import EmailTool

__all__ = [
    "Tool", "ToolResult", "TransientError", "PermanentError",
    "CRMTool", "CalendarTool", "EmailTool"
]
