"""
Base tool abstraction with structured result handling.
All tools return ToolResult with success/failure status.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from observability import trace_logger


@dataclass
class ToolResult:
    """Structured result from tool execution."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_allowed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "retry_allowed": self.retry_allowed
        }


class Tool(ABC):
    """Abstract base class for all tools."""

    def __init__(self, name: str):
        self.name = name
        self.retry_count = 0
        self.max_retries = 3

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """Execute tool with parameters."""
        pass

    def execute_with_retry(self, **kwargs) -> ToolResult:
        """
        Execute tool with automatic retry on transient failures.

        Retries up to max_retries times with exponential backoff.
        Only retries if result indicates retry_allowed=True.
        """
        self.retry_count = 0

        while self.retry_count <= self.max_retries:
            try:
                trace_logger.tool_called(
                    tool_name=self.name,
                    parameters=kwargs,
                    retry_count=self.retry_count
                )

                result = self.execute(**kwargs)

                trace_logger.tool_result(
                    tool_name=self.name,
                    success=result.success,
                    data=result.data,
                    error=result.error,
                    retry_count=self.retry_count
                )

                # If success or no retry allowed, return
                if result.success or not result.retry_allowed:
                    return result

                # Retry on transient failure
                self.retry_count += 1
                if self.retry_count <= self.max_retries:
                    trace_logger.info(
                        f"Retrying {self.name} (attempt {self.retry_count}/{self.max_retries})",
                        error=result.error
                    )
                    continue
                else:
                    # Max retries exceeded
                    return result

            except Exception as e:
                error_msg = f"Tool execution exception: {str(e)}"
                trace_logger.error_occurred(
                    error_type="tool_execution_exception",
                    error_message=error_msg,
                    context={"tool": self.name, "params": kwargs}
                )

                result = ToolResult(
                    success=False,
                    error=error_msg,
                    retry_allowed=False  # Don't retry on exceptions
                )

                trace_logger.tool_result(
                    tool_name=self.name,
                    success=False,
                    error=error_msg,
                    retry_count=self.retry_count
                )

                return result

        # Should not reach here, but safety return
        return ToolResult(
            success=False,
            error="Max retries exceeded",
            retry_allowed=False
        )


class TransientError(Exception):
    """Exception for transient errors that should be retried."""
    pass


class PermanentError(Exception):
    """Exception for permanent errors that should not be retried."""
    pass
