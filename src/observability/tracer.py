"""
LastAgent Tracer

Distributed tracing with span management for request correlation.
"""
from __future__ import annotations

import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Generator

from .logger import set_trace_context, get_trace_context, clear_trace_context


# =============================================================================
# SPAN STATUS
# =============================================================================
class SpanStatus(str, Enum):
    """Status of a span."""
    STARTED = "started"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"


# =============================================================================
# SPAN
# =============================================================================
@dataclass
class Span:
    """A single execution span within a trace."""
    span_id: str
    trace_id: str
    name: str
    parent_span_id: str | None = None
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: datetime | None = None
    status: SpanStatus = SpanStatus.STARTED
    component: str | None = None
    phase: str | None = None
    agent: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    error: dict[str, Any] | None = None
    
    @property
    def duration_ms(self) -> float | None:
        """Get span duration in milliseconds."""
        if self.end_time is None:
            return None
        delta = self.end_time - self.start_time
        return delta.total_seconds() * 1000
    
    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        """Add an event to the span."""
        self.events.append({
            "name": name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "attributes": attributes or {},
        })
    
    def set_attribute(self, key: str, value: Any) -> None:
        """Set a span attribute."""
        self.attributes[key] = value
    
    def set_status(self, status: SpanStatus, message: str | None = None) -> None:
        """Set span status."""
        self.status = status
        if message:
            self.set_attribute("status_message", message)
    
    def set_error(
        self,
        error_type: str,
        message: str,
        classification: str | None = None,
    ) -> None:
        """Set error information."""
        self.status = SpanStatus.ERROR
        self.error = {
            "type": error_type,
            "message": message,
            "classification": classification,
        }
    
    def end(self, status: SpanStatus = SpanStatus.SUCCESS) -> None:
        """End the span."""
        self.end_time = datetime.now(timezone.utc)
        if self.status == SpanStatus.STARTED or self.status == SpanStatus.RUNNING:
            self.status = status
    
    def to_dict(self) -> dict[str, Any]:
        """Convert span to dictionary."""
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "name": self.name,
            "parent_span_id": self.parent_span_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "status": self.status.value,
            "component": self.component,
            "phase": self.phase,
            "agent": self.agent,
            "attributes": self.attributes,
            "events": self.events,
            "error": self.error,
        }


# =============================================================================
# TRACER
# =============================================================================
class Tracer:
    """Manages traces and spans for request correlation."""
    
    def __init__(self, service_name: str = "lastagent"):
        self.service_name = service_name
        self._spans: dict[str, Span] = {}
        self._trace_spans: dict[str, list[str]] = {}  # trace_id -> [span_ids]
        
    def _generate_id(self) -> str:
        """Generate a unique ID."""
        return str(uuid.uuid4())[:16]
    
    def start_trace(self, name: str = "request") -> Span:
        """Start a new trace with root span."""
        trace_id = self._generate_id()
        span = self.start_span(name, trace_id=trace_id)
        return span
    
    def start_span(
        self,
        name: str,
        trace_id: str | None = None,
        parent_span_id: str | None = None,
        component: str | None = None,
        phase: str | None = None,
        agent: str | None = None,
    ) -> Span:
        """Start a new span."""
        # Use current context if not provided
        ctx = get_trace_context()
        trace_id = trace_id or ctx["trace_id"] or self._generate_id()
        parent_span_id = parent_span_id or ctx["span_id"]
        
        span = Span(
            span_id=self._generate_id(),
            trace_id=trace_id,
            name=name,
            parent_span_id=parent_span_id,
            component=component or ctx["component"],
            phase=phase or ctx["phase"],
            agent=agent or ctx["agent"],
        )
        
        # Store span
        self._spans[span.span_id] = span
        if trace_id not in self._trace_spans:
            self._trace_spans[trace_id] = []
        self._trace_spans[trace_id].append(span.span_id)
        
        # Update context
        set_trace_context(
            trace_id=trace_id,
            span_id=span.span_id,
            parent_span_id=parent_span_id,
            component=component,
            phase=phase,
            agent=agent,
        )
        
        return span
    
    def end_span(self, span: Span, status: SpanStatus = SpanStatus.SUCCESS) -> None:
        """End a span and restore parent context."""
        span.end(status)
        
        # Restore parent context
        if span.parent_span_id:
            parent = self._spans.get(span.parent_span_id)
            if parent:
                set_trace_context(
                    span_id=parent.span_id,
                    component=parent.component,
                    phase=parent.phase,
                    agent=parent.agent,
                )
    
    def get_span(self, span_id: str) -> Span | None:
        """Get a span by ID."""
        return self._spans.get(span_id)
    
    def get_trace_spans(self, trace_id: str) -> list[Span]:
        """Get all spans for a trace."""
        span_ids = self._trace_spans.get(trace_id, [])
        return [self._spans[sid] for sid in span_ids if sid in self._spans]
    
    def get_trace_tree(self, trace_id: str) -> dict[str, Any]:
        """Get trace as a tree structure."""
        spans = self.get_trace_spans(trace_id)
        if not spans:
            return {}
        
        # Build tree
        span_map = {s.span_id: s.to_dict() for s in spans}
        for span in spans:
            span_map[span.span_id]["children"] = []
        
        root = None
        for span in spans:
            if span.parent_span_id and span.parent_span_id in span_map:
                span_map[span.parent_span_id]["children"].append(span_map[span.span_id])
            elif span.parent_span_id is None:
                root = span_map[span.span_id]
        
        return root or {}
    
    def clear_trace(self, trace_id: str) -> None:
        """Clear all spans for a trace."""
        span_ids = self._trace_spans.pop(trace_id, [])
        for span_id in span_ids:
            self._spans.pop(span_id, None)
        clear_trace_context()


# =============================================================================
# CONTEXT MANAGER
# =============================================================================
@contextmanager
def trace_context(
    tracer: Tracer,
    name: str,
    component: str | None = None,
    phase: str | None = None,
    agent: str | None = None,
) -> Generator[Span, None, None]:
    """Context manager for automatic span management."""
    span = tracer.start_span(
        name=name,
        component=component,
        phase=phase,
        agent=agent,
    )
    try:
        span.set_status(SpanStatus.RUNNING)
        yield span
        tracer.end_span(span, SpanStatus.SUCCESS)
    except Exception as e:
        span.set_error(
            error_type=type(e).__name__,
            message=str(e),
        )
        tracer.end_span(span, SpanStatus.ERROR)
        raise


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================
_tracer: Tracer | None = None


def get_tracer() -> Tracer:
    """Get the global tracer instance."""
    global _tracer
    if _tracer is None:
        _tracer = Tracer()
    return _tracer
