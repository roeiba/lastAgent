"""
LastAgent Error Tracker

Error classification and root cause analysis for debugging.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


# =============================================================================
# ERROR CLASSIFICATION
# =============================================================================
class ErrorClassification(str, Enum):
    """Classification of error types."""
    TIMEOUT = "timeout"
    API_ERROR = "api_error"
    VALIDATION_ERROR = "validation_error"
    AUTHORIZATION_ERROR = "authorization_error"
    RATE_LIMIT = "rate_limit"
    NETWORK_ERROR = "network_error"
    AGENT_ERROR = "agent_error"
    DELEGATION_ERROR = "delegation_error"
    CONFIGURATION_ERROR = "configuration_error"
    INTERNAL_ERROR = "internal_error"
    UNKNOWN = "unknown"
    
    @classmethod
    def from_exception(cls, exc: Exception) -> "ErrorClassification":
        """Classify an exception."""
        exc_type = type(exc).__name__
        
        # Map common exception types
        if "Timeout" in exc_type:
            return cls.TIMEOUT
        elif "API" in exc_type or "HTTPError" in exc_type:
            return cls.API_ERROR
        elif "Validation" in exc_type or "ValueError" in exc_type:
            return cls.VALIDATION_ERROR
        elif "Auth" in exc_type or "Permission" in exc_type:
            return cls.AUTHORIZATION_ERROR
        elif "RateLimit" in exc_type:
            return cls.RATE_LIMIT
        elif "Connection" in exc_type or "Network" in exc_type:
            return cls.NETWORK_ERROR
        elif "Config" in exc_type or "KeyError" in exc_type:
            return cls.CONFIGURATION_ERROR
        else:
            return cls.UNKNOWN


# =============================================================================
# ERROR RECORD
# =============================================================================
@dataclass
class ErrorRecord:
    """A recorded error with context."""
    error_id: str
    trace_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error_type: str = ""
    message: str = ""
    classification: ErrorClassification = ErrorClassification.UNKNOWN
    recoverable: bool = False
    phase: str | None = None
    agent: str | None = None
    component: str | None = None
    stack_trace: str | None = None
    execution_context: dict[str, Any] = field(default_factory=dict)
    timeline_summary: list[dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "error_id": self.error_id,
            "trace_id": self.trace_id,
            "timestamp": self.timestamp.isoformat(),
            "error_type": self.error_type,
            "message": self.message,
            "classification": self.classification.value,
            "recoverable": self.recoverable,
            "phase": self.phase,
            "agent": self.agent,
            "component": self.component,
            "stack_trace": self.stack_trace,
            "execution_context": self.execution_context,
            "timeline_summary": self.timeline_summary,
        }


# =============================================================================
# ERROR TRACKER
# =============================================================================
class ErrorTracker:
    """Tracks and classifies errors for debugging."""
    
    def __init__(self, max_errors: int = 500):
        self._errors: list[ErrorRecord] = []
        self._max_errors = max_errors
        self._error_counts: dict[ErrorClassification, int] = {
            c: 0 for c in ErrorClassification
        }
    
    def _generate_id(self) -> str:
        """Generate error ID."""
        import uuid
        return f"err_{uuid.uuid4().hex[:12]}"
    
    def record_error(
        self,
        trace_id: str,
        error_type: str,
        message: str,
        classification: ErrorClassification | None = None,
        recoverable: bool = False,
        phase: str | None = None,
        agent: str | None = None,
        component: str | None = None,
        stack_trace: str | None = None,
        execution_context: dict[str, Any] | None = None,
        timeline_summary: list[dict[str, Any]] | None = None,
    ) -> ErrorRecord:
        """Record an error."""
        if classification is None:
            classification = self._classify_error(error_type, message)
        
        record = ErrorRecord(
            error_id=self._generate_id(),
            trace_id=trace_id,
            error_type=error_type,
            message=message,
            classification=classification,
            recoverable=recoverable,
            phase=phase,
            agent=agent,
            component=component,
            stack_trace=stack_trace,
            execution_context=execution_context or {},
            timeline_summary=timeline_summary or [],
        )
        
        # Store error
        self._errors.append(record)
        self._error_counts[classification] += 1
        
        # Evict old errors if at capacity
        if len(self._errors) > self._max_errors:
            self._errors = self._errors[-self._max_errors:]
        
        return record
    
    def record_exception(
        self,
        trace_id: str,
        exc: Exception,
        phase: str | None = None,
        agent: str | None = None,
        component: str | None = None,
        execution_context: dict[str, Any] | None = None,
        timeline_summary: list[dict[str, Any]] | None = None,
    ) -> ErrorRecord:
        """Record an error from an exception."""
        import traceback
        
        return self.record_error(
            trace_id=trace_id,
            error_type=type(exc).__name__,
            message=str(exc),
            classification=ErrorClassification.from_exception(exc),
            recoverable=self._is_recoverable(exc),
            phase=phase,
            agent=agent,
            component=component,
            stack_trace=traceback.format_exc(),
            execution_context=execution_context,
            timeline_summary=timeline_summary,
        )
    
    def _classify_error(self, error_type: str, message: str) -> ErrorClassification:
        """Classify an error based on type and message."""
        lower_msg = message.lower()
        
        if "timeout" in lower_msg:
            return ErrorClassification.TIMEOUT
        elif "rate limit" in lower_msg or "429" in message:
            return ErrorClassification.RATE_LIMIT
        elif "auth" in lower_msg or "401" in message or "403" in message:
            return ErrorClassification.AUTHORIZATION_ERROR
        elif "valid" in lower_msg:
            return ErrorClassification.VALIDATION_ERROR
        elif "connect" in lower_msg or "network" in lower_msg:
            return ErrorClassification.NETWORK_ERROR
        elif "api" in lower_msg or "500" in message:
            return ErrorClassification.API_ERROR
        elif "config" in lower_msg:
            return ErrorClassification.CONFIGURATION_ERROR
        else:
            return ErrorClassification.UNKNOWN
    
    def _is_recoverable(self, exc: Exception) -> bool:
        """Determine if an error is recoverable."""
        # Most transient errors are recoverable
        classification = ErrorClassification.from_exception(exc)
        return classification in [
            ErrorClassification.TIMEOUT,
            ErrorClassification.RATE_LIMIT,
            ErrorClassification.NETWORK_ERROR,
        ]
    
    def get_recent_errors(self, limit: int = 10) -> list[ErrorRecord]:
        """Get recent errors."""
        return self._errors[-limit:]
    
    def get_errors_by_trace(self, trace_id: str) -> list[ErrorRecord]:
        """Get all errors for a trace."""
        return [e for e in self._errors if e.trace_id == trace_id]
    
    def get_errors_by_classification(
        self,
        classification: ErrorClassification,
        limit: int = 10,
    ) -> list[ErrorRecord]:
        """Get errors by classification."""
        return [
            e for e in self._errors
            if e.classification == classification
        ][-limit:]
    
    def get_error_stats(self) -> dict[str, Any]:
        """Get error statistics."""
        total = sum(self._error_counts.values())
        return {
            "total_errors": total,
            "by_classification": {
                c.value: count
                for c, count in self._error_counts.items()
                if count > 0
            },
            "recoverable_rate": sum(
                1 for e in self._errors if e.recoverable
            ) / max(len(self._errors), 1),
        }
    
    def clear(self) -> None:
        """Clear all recorded errors."""
        self._errors = []
        self._error_counts = {c: 0 for c in ErrorClassification}


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================
_error_tracker: ErrorTracker | None = None


def get_error_tracker() -> ErrorTracker:
    """Get the global error tracker."""
    global _error_tracker
    if _error_tracker is None:
        _error_tracker = ErrorTracker()
    return _error_tracker
