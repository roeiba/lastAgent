"""
LastAgent Execution Timeline

Visualizes the execution flow of agent interactions for debugging.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


# =============================================================================
# TIMELINE EVENT TYPES
# =============================================================================
class EventType(str, Enum):
    """Types of timeline events."""
    TASK_RECEIVED = "task_received"
    SELECTION_START = "selection_start"
    SELECTION_VOTE = "selection_vote"
    SELECTION_COMPLETE = "selection_complete"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_DENIED = "approval_denied"
    EXECUTION_START = "execution_start"
    EXECUTION_COMPLETE = "execution_complete"
    DELEGATION_START = "delegation_start"
    DELEGATION_COMPLETE = "delegation_complete"
    ERROR = "error"
    RESPONSE_SENT = "response_sent"


# =============================================================================
# TIMELINE EVENT
# =============================================================================
@dataclass
class TimelineEvent:
    """A single event in the execution timeline."""
    event_type: EventType
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    phase: str | None = None
    agent: str | None = None
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    duration_ms: float | None = None
    status: str = "success"
    error: dict[str, Any] | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        d = {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "phase": self.phase,
            "agent": self.agent,
            "message": self.message,
            "status": self.status,
        }
        if self.data:
            d["data"] = self.data
        if self.duration_ms is not None:
            d["duration_ms"] = self.duration_ms
        if self.error:
            d["error"] = self.error
        return d


# =============================================================================
# EXECUTION TIMELINE
# =============================================================================
@dataclass
class ExecutionTimeline:
    """Records the full execution timeline for a request."""
    trace_id: str
    events: list[TimelineEvent] = field(default_factory=list)
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: datetime | None = None
    
    @property
    def total_duration_ms(self) -> float | None:
        """Get total timeline duration."""
        if self.end_time is None:
            return None
        delta = self.end_time - self.start_time
        return delta.total_seconds() * 1000
    
    def add_event(
        self,
        event_type: EventType,
        phase: str | None = None,
        agent: str | None = None,
        message: str = "",
        data: dict[str, Any] | None = None,
        duration_ms: float | None = None,
        status: str = "success",
        error: dict[str, Any] | None = None,
    ) -> TimelineEvent:
        """Add an event to the timeline."""
        event = TimelineEvent(
            event_type=event_type,
            phase=phase,
            agent=agent,
            message=message,
            data=data or {},
            duration_ms=duration_ms,
            status=status,
            error=error,
        )
        self.events.append(event)
        return event
    
    def record_task_received(self, task_preview: str) -> TimelineEvent:
        """Record task received event."""
        return self.add_event(
            EventType.TASK_RECEIVED,
            phase="INTAKE",
            message="Task received",
            data={"task_preview": task_preview[:100]},
        )
    
    def record_selection_start(self, available_agents: list[str]) -> TimelineEvent:
        """Record council selection start."""
        return self.add_event(
            EventType.SELECTION_START,
            phase="SELECTION",
            message="Council voting started",
            data={"available_agents": available_agents},
        )
    
    def record_selection_vote(self, model: str, vote: str) -> TimelineEvent:
        """Record a council vote."""
        return self.add_event(
            EventType.SELECTION_VOTE,
            phase="SELECTION",
            message=f"Vote from {model}",
            data={"model": model, "vote": vote},
        )
    
    def record_selection_complete(
        self,
        selected_agent: str,
        duration_ms: float,
        reasoning: str = "",
    ) -> TimelineEvent:
        """Record selection complete."""
        return self.add_event(
            EventType.SELECTION_COMPLETE,
            phase="SELECTION",
            agent=selected_agent,
            message=f"Selected agent: {selected_agent}",
            data={"reasoning": reasoning},
            duration_ms=duration_ms,
        )
    
    def record_execution_start(self, agent: str) -> TimelineEvent:
        """Record execution start."""
        return self.add_event(
            EventType.EXECUTION_START,
            phase="EXECUTION",
            agent=agent,
            message=f"Executing with {agent}",
        )
    
    def record_execution_complete(
        self,
        agent: str,
        duration_ms: float,
        status: str = "success",
    ) -> TimelineEvent:
        """Record execution complete."""
        return self.add_event(
            EventType.EXECUTION_COMPLETE,
            phase="EXECUTION",
            agent=agent,
            message=f"Execution complete: {agent}",
            duration_ms=duration_ms,
            status=status,
        )
    
    def record_delegation(
        self,
        from_agent: str,
        to_agent: str,
        task: str,
    ) -> TimelineEvent:
        """Record delegation request."""
        return self.add_event(
            EventType.DELEGATION_START,
            phase="DELEGATION",
            agent=to_agent,
            message=f"{from_agent} → {to_agent}",
            data={"from_agent": from_agent, "task": task[:100]},
        )
    
    def record_error(
        self,
        agent: str | None,
        error_type: str,
        error_message: str,
        phase: str = "EXECUTION",
    ) -> TimelineEvent:
        """Record an error event."""
        return self.add_event(
            EventType.ERROR,
            phase=phase,
            agent=agent,
            message=error_message,
            status="error",
            error={"type": error_type, "message": error_message},
        )
    
    def finalize(self) -> None:
        """Finalize the timeline."""
        self.end_time = datetime.now(timezone.utc)
        self.add_event(
            EventType.RESPONSE_SENT,
            phase="COMPLETE",
            message="Response sent",
            duration_ms=self.total_duration_ms,
        )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert timeline to dictionary."""
        return {
            "trace_id": self.trace_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_duration_ms": self.total_duration_ms,
            "event_count": len(self.events),
            "events": [e.to_dict() for e in self.events],
        }
    
    def to_summary(self) -> list[dict[str, Any]]:
        """Get a compact summary of key events."""
        key_events = [
            EventType.SELECTION_COMPLETE,
            EventType.EXECUTION_COMPLETE,
            EventType.DELEGATION_START,
            EventType.ERROR,
        ]
        return [
            {"phase": e.phase, "agent": e.agent, "duration_ms": e.duration_ms, "status": e.status}
            for e in self.events
            if e.event_type in key_events
        ]


# =============================================================================
# TIMELINE MANAGER
# =============================================================================
class TimelineManager:
    """Manages execution timelines for multiple requests."""
    
    def __init__(self, max_timelines: int = 100):
        self._timelines: dict[str, ExecutionTimeline] = {}
        self._max_timelines = max_timelines
    
    def create_timeline(self, trace_id: str) -> ExecutionTimeline:
        """Create a new timeline."""
        # Evict old timelines if at capacity
        if len(self._timelines) >= self._max_timelines:
            oldest_key = next(iter(self._timelines))
            del self._timelines[oldest_key]
        
        timeline = ExecutionTimeline(trace_id=trace_id)
        self._timelines[trace_id] = timeline
        return timeline
    
    def get_timeline(self, trace_id: str) -> ExecutionTimeline | None:
        """Get a timeline by trace ID."""
        return self._timelines.get(trace_id)
    
    def finalize_timeline(self, trace_id: str) -> ExecutionTimeline | None:
        """Finalize a timeline."""
        timeline = self._timelines.get(trace_id)
        if timeline:
            timeline.finalize()
        return timeline


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================
_timeline_manager: TimelineManager | None = None


def get_timeline() -> TimelineManager:
    """Get the global timeline manager."""
    global _timeline_manager
    if _timeline_manager is None:
        _timeline_manager = TimelineManager()
    return _timeline_manager
