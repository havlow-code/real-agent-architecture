"""
Structured logging with trace IDs for observability.
All agent decisions, tool calls, and errors are logged.
"""

import logging
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List
from pathlib import Path
from contextlib import contextmanager
from pythonjsonlogger import jsonlogger

from config import settings


class TraceLogger:
    """Structured logger with trace ID support for agent observability."""

    def __init__(self, name: str = "autonomous_agent"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, settings.log_level))

        # Ensure log directory exists
        log_file_path = Path(settings.log_file)
        log_file_path.parent.mkdir(parents=True, exist_ok=True)

        # File handler with JSON formatting
        file_handler = logging.FileHandler(settings.log_file)
        json_formatter = jsonlogger.JsonFormatter(
            fmt='%(asctime)s %(name)s %(levelname)s %(message)s',
            rename_fields={'levelname': 'level', 'asctime': 'timestamp'}
        )
        file_handler.setFormatter(json_formatter)
        self.logger.addHandler(file_handler)

        # Console handler with readable formatting
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # Thread-local storage for trace IDs
        self._current_trace_id: Optional[str] = None

    def generate_trace_id(self) -> str:
        """Generate a new trace ID."""
        return str(uuid.uuid4())

    @contextmanager
    def trace(self, trace_id: Optional[str] = None):
        """Context manager for trace ID."""
        old_trace_id = self._current_trace_id
        self._current_trace_id = trace_id or self.generate_trace_id()
        try:
            yield self._current_trace_id
        finally:
            self._current_trace_id = old_trace_id

    def _log(self, level: str, event: str, **kwargs):
        """Internal log method with trace ID."""
        log_data = {
            "trace_id": self._current_trace_id or "unknown",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            **kwargs
        }

        log_method = getattr(self.logger, level.lower())
        log_method(json.dumps(log_data), extra=log_data)

    def decision_made(
        self,
        decision: str,
        confidence: float,
        reasoning: str,
        **kwargs
    ):
        """Log agent decision."""
        self._log(
            "info",
            "decision_made",
            decision=decision,
            confidence=confidence,
            reasoning=reasoning,
            **kwargs
        )

    def retrieval_performed(
        self,
        query: str,
        sources: List[Dict[str, Any]],
        top_k: int,
        **kwargs
    ):
        """Log RAG retrieval."""
        self._log(
            "info",
            "retrieval_performed",
            query=query,
            num_sources=len(sources),
            top_k=top_k,
            sources=[
                {
                    "source_id": s.get("source_id"),
                    "score": s.get("score"),
                    "doc_title": s.get("doc_title")
                }
                for s in sources
            ],
            **kwargs
        )

    def tool_called(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        **kwargs
    ):
        """Log tool invocation."""
        self._log(
            "info",
            "tool_called",
            tool_name=tool_name,
            parameters=parameters,
            **kwargs
        )

    def tool_result(
        self,
        tool_name: str,
        success: bool,
        data: Optional[Dict] = None,
        error: Optional[str] = None,
        retry_count: int = 0,
        **kwargs
    ):
        """Log tool result."""
        self._log(
            "info" if success else "warning",
            "tool_result",
            tool_name=tool_name,
            success=success,
            data=data,
            error=error,
            retry_count=retry_count,
            **kwargs
        )

    def confidence_calculated(
        self,
        confidence: float,
        factors: Dict[str, Any],
        threshold_met: bool,
        **kwargs
    ):
        """Log confidence calculation."""
        self._log(
            "info",
            "confidence_calculated",
            confidence=confidence,
            factors=factors,
            threshold_met=threshold_met,
            **kwargs
        )

    def escalation_triggered(
        self,
        reason: str,
        confidence: float,
        context: Dict[str, Any],
        **kwargs
    ):
        """Log human escalation."""
        self._log(
            "warning",
            "escalation_triggered",
            reason=reason,
            confidence=confidence,
            context=context,
            **kwargs
        )

    def response_composed(
        self,
        response_text: str,
        grounded: bool,
        sources_used: List[str],
        **kwargs
    ):
        """Log response composition."""
        self._log(
            "info",
            "response_composed",
            response_length=len(response_text),
            grounded=grounded,
            num_sources=len(sources_used),
            sources_used=sources_used,
            **kwargs
        )

    def memory_updated(
        self,
        memory_type: str,
        lead_id: str,
        operation: str,
        **kwargs
    ):
        """Log memory update."""
        self._log(
            "info",
            "memory_updated",
            memory_type=memory_type,
            lead_id=lead_id,
            operation=operation,
            **kwargs
        )

    def error_occurred(
        self,
        error_type: str,
        error_message: str,
        context: Optional[Dict] = None,
        **kwargs
    ):
        """Log error."""
        self._log(
            "error",
            "error_occurred",
            error_type=error_type,
            error_message=error_message,
            context=context or {},
            **kwargs
        )

    def agent_run_started(
        self,
        lead_id: str,
        message: str,
        source: str,
        **kwargs
    ):
        """Log agent run start."""
        self._log(
            "info",
            "agent_run_started",
            lead_id=lead_id,
            message_preview=message[:100],
            source=source,
            **kwargs
        )

    def agent_run_completed(
        self,
        lead_id: str,
        success: bool,
        duration_ms: float,
        **kwargs
    ):
        """Log agent run completion."""
        self._log(
            "info",
            "agent_run_completed",
            lead_id=lead_id,
            success=success,
            duration_ms=duration_ms,
            **kwargs
        )

    def debug(self, message: str, **kwargs):
        """Debug level log."""
        self._log("debug", "debug", message=message, **kwargs)

    def info(self, message: str, **kwargs):
        """Info level log."""
        self._log("info", "info", message=message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Warning level log."""
        self._log("warning", "warning", message=message, **kwargs)

    def error(self, message: str, **kwargs):
        """Error level log."""
        self._log("error", "error", message=message, **kwargs)


# Global logger instance
trace_logger = TraceLogger()
