"""
LastAgent Structured Logger

Enterprise-grade JSON structured logging with trace correlation.
"""
from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any


# =============================================================================
# LOG LEVELS
# =============================================================================
class LogLevel(str, Enum):
    """Log level enumeration."""
    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    
    @classmethod
    def from_string(cls, level: str) -> "LogLevel":
        """Convert string to LogLevel."""
        return cls[level.upper()]
    
    def to_python_level(self) -> int:
        """Convert to Python logging level."""
        mapping = {
            LogLevel.TRACE: 5,  # Custom level below DEBUG
            LogLevel.DEBUG: logging.DEBUG,
            LogLevel.INFO: logging.INFO,
            LogLevel.WARN: logging.WARNING,
            LogLevel.ERROR: logging.ERROR,
        }
        return mapping[self]


# =============================================================================
# CONTEXT VARIABLES
# =============================================================================
_trace_id: ContextVar[str | None] = ContextVar("trace_id", default=None)
_span_id: ContextVar[str | None] = ContextVar("span_id", default=None)
_parent_span_id: ContextVar[str | None] = ContextVar("parent_span_id", default=None)
_component: ContextVar[str | None] = ContextVar("component", default=None)
_phase: ContextVar[str | None] = ContextVar("phase", default=None)
_agent: ContextVar[str | None] = ContextVar("agent", default=None)


def set_trace_context(
    trace_id: str | None = None,
    span_id: str | None = None,
    parent_span_id: str | None = None,
    component: str | None = None,
    phase: str | None = None,
    agent: str | None = None,
) -> None:
    """Set the current trace context."""
    if trace_id is not None:
        _trace_id.set(trace_id)
    if span_id is not None:
        _span_id.set(span_id)
    if parent_span_id is not None:
        _parent_span_id.set(parent_span_id)
    if component is not None:
        _component.set(component)
    if phase is not None:
        _phase.set(phase)
    if agent is not None:
        _agent.set(agent)


def get_trace_context() -> dict[str, str | None]:
    """Get the current trace context."""
    return {
        "trace_id": _trace_id.get(),
        "span_id": _span_id.get(),
        "parent_span_id": _parent_span_id.get(),
        "component": _component.get(),
        "phase": _phase.get(),
        "agent": _agent.get(),
    }


def clear_trace_context() -> None:
    """Clear the current trace context."""
    _trace_id.set(None)
    _span_id.set(None)
    _parent_span_id.set(None)
    _component.set(None)
    _phase.set(None)
    _agent.set(None)


# =============================================================================
# STRUCTURED LOG ENTRY
# =============================================================================
@dataclass
class LogEntry:
    """Structured log entry."""
    timestamp: str
    level: str
    message: str
    trace_id: str | None = None
    span_id: str | None = None
    parent_span_id: str | None = None
    component: str | None = None
    phase: str | None = None
    agent: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    duration_ms: float | None = None
    error: dict[str, Any] | None = None
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        d = asdict(self)
        # Remove None values for cleaner output
        d = {k: v for k, v in d.items() if v is not None}
        return json.dumps(d)
    
    @classmethod
    def create(
        cls,
        level: str,
        message: str,
        data: dict[str, Any] | None = None,
        duration_ms: float | None = None,
        error: dict[str, Any] | None = None,
    ) -> "LogEntry":
        """Create a log entry with current trace context."""
        ctx = get_trace_context()
        return cls(
            timestamp=datetime.now(timezone.utc).isoformat(),
            level=level,
            message=message,
            trace_id=ctx["trace_id"],
            span_id=ctx["span_id"],
            parent_span_id=ctx["parent_span_id"],
            component=ctx["component"],
            phase=ctx["phase"],
            agent=ctx["agent"],
            data=data or {},
            duration_ms=duration_ms,
            error=error,
        )


# =============================================================================
# JSON LOG FORMATTER
# =============================================================================
class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""
    
    def __init__(self, include_trace: bool = True):
        super().__init__()
        self.include_trace = include_trace
        
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        entry = LogEntry.create(
            level=record.levelname,
            message=record.getMessage(),
            data=getattr(record, "data", {}),
            duration_ms=getattr(record, "duration_ms", None),
            error=getattr(record, "error", None),
        )
        return entry.to_json()


# =============================================================================
# STRUCTURED LOGGER
# =============================================================================
class StructuredLogger:
    """Logger with structured JSON output and trace context."""
    
    def __init__(self, name: str, level: LogLevel = LogLevel.INFO):
        self.name = name
        self._logger = logging.getLogger(name)
        self._configure(level)
        
    def _configure(self, level: LogLevel) -> None:
        """Configure the logger with JSON handler."""
        self._logger.setLevel(level.to_python_level())
        
        # Remove existing handlers
        self._logger.handlers = []
        
        # Add JSON handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        self._logger.addHandler(handler)
        
        # Don't propagate to root logger
        self._logger.propagate = False
        
    def _log(
        self,
        level: int,
        message: str,
        data: dict[str, Any] | None = None,
        duration_ms: float | None = None,
        error: dict[str, Any] | None = None,
    ) -> None:
        """Internal log method."""
        extra = {
            "data": data or {},
            "duration_ms": duration_ms,
            "error": error,
        }
        self._logger.log(level, message, extra=extra)
        
    def trace(self, message: str, **data: Any) -> None:
        """Log at TRACE level."""
        self._log(5, message, data=data)
        
    def debug(self, message: str, **data: Any) -> None:
        """Log at DEBUG level."""
        self._log(logging.DEBUG, message, data=data)
        
    def info(self, message: str, **data: Any) -> None:
        """Log at INFO level."""
        self._log(logging.INFO, message, data=data)
        
    def warn(self, message: str, **data: Any) -> None:
        """Log at WARN level."""
        self._log(logging.WARNING, message, data=data)
        
    def error(
        self,
        message: str,
        error_type: str | None = None,
        error_message: str | None = None,
        **data: Any,
    ) -> None:
        """Log at ERROR level with error details."""
        error_data = None
        if error_type or error_message:
            error_data = {
                "type": error_type or "UnknownError",
                "message": error_message or message,
            }
        self._log(logging.ERROR, message, data=data, error=error_data)
        
    def with_duration(
        self,
        message: str,
        duration_ms: float,
        level: LogLevel = LogLevel.INFO,
        **data: Any,
    ) -> None:
        """Log with duration timing."""
        self._log(level.to_python_level(), message, data=data, duration_ms=duration_ms)


# =============================================================================
# GLOBAL INSTANCES
# =============================================================================
_loggers: dict[str, StructuredLogger] = {}
_default_level: LogLevel = LogLevel.INFO


def configure_logging(level: LogLevel = LogLevel.INFO) -> None:
    """Configure default logging level."""
    global _default_level
    _default_level = level
    
    # Register custom TRACE level
    logging.addLevelName(5, "TRACE")


def get_logger(name: str = "lastagent") -> StructuredLogger:
    """Get or create a structured logger."""
    if name not in _loggers:
        _loggers[name] = StructuredLogger(name, _default_level)
    return _loggers[name]
