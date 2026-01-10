"""
LastAgent Observability Module

Enterprise-grade end-to-end logging, tracing, and debugging capabilities.
"""
from .logger import (
    get_logger,
    configure_logging,
    LogLevel,
)
from .tracer import (
    Tracer,
    Span,
    get_tracer,
    trace_context,
)
from .timeline import (
    ExecutionTimeline,
    TimelineEvent,
    get_timeline,
)
from .error_tracker import (
    ErrorTracker,
    ErrorClassification,
    get_error_tracker,
)

__all__ = [
    # Logger
    "get_logger",
    "configure_logging",
    "LogLevel",
    # Tracer
    "Tracer",
    "Span",
    "get_tracer",
    "trace_context",
    # Timeline
    "ExecutionTimeline",
    "TimelineEvent",
    "get_timeline",
    # Error Tracker
    "ErrorTracker",
    "ErrorClassification",
    "get_error_tracker",
]
