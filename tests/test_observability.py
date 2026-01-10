"""
Tests for LastAgent Observability Module
"""
import pytest
from datetime import datetime, timezone

from src.observability.logger import (
    LogLevel,
    LogEntry,
    StructuredLogger,
    set_trace_context,
    get_trace_context,
    clear_trace_context,
    get_logger,
    configure_logging,
)
from src.observability.tracer import (
    Span,
    SpanStatus,
    Tracer,
    trace_context,
    get_tracer,
)
from src.observability.timeline import (
    EventType,
    TimelineEvent,
    ExecutionTimeline,
    TimelineManager,
    get_timeline,
)
from src.observability.error_tracker import (
    ErrorClassification,
    ErrorRecord,
    ErrorTracker,
    get_error_tracker,
)


# =============================================================================
# LOGGER TESTS
# =============================================================================
class TestLogLevel:
    """Tests for LogLevel enum."""
    
    def test_from_string(self):
        """Test converting string to LogLevel."""
        assert LogLevel.from_string("info") == LogLevel.INFO
        assert LogLevel.from_string("DEBUG") == LogLevel.DEBUG
        
    def test_to_python_level(self):
        """Test converting to Python logging level."""
        assert LogLevel.INFO.to_python_level() == 20
        assert LogLevel.ERROR.to_python_level() == 40


class TestTraceContext:
    """Tests for trace context functions."""
    
    def setup_method(self):
        """Clear context before each test."""
        clear_trace_context()
        
    def test_set_and_get_context(self):
        """Test setting and getting trace context."""
        set_trace_context(trace_id="test-trace", span_id="test-span")
        ctx = get_trace_context()
        assert ctx["trace_id"] == "test-trace"
        assert ctx["span_id"] == "test-span"
        
    def test_clear_context(self):
        """Test clearing trace context."""
        set_trace_context(trace_id="test")
        clear_trace_context()
        ctx = get_trace_context()
        assert ctx["trace_id"] is None


class TestLogEntry:
    """Tests for LogEntry dataclass."""
    
    def test_to_json(self):
        """Test JSON serialization."""
        entry = LogEntry(
            timestamp="2026-01-10T12:00:00Z",
            level="INFO",
            message="Test message",
        )
        json_str = entry.to_json()
        assert "Test message" in json_str
        assert "INFO" in json_str
        
    def test_create_with_context(self):
        """Test creating entry with trace context."""
        set_trace_context(trace_id="ctx-trace", span_id="ctx-span")
        entry = LogEntry.create("INFO", "Test")
        assert entry.trace_id == "ctx-trace"
        assert entry.span_id == "ctx-span"
        clear_trace_context()


class TestStructuredLogger:
    """Tests for StructuredLogger class."""
    
    def test_logger_creation(self):
        """Test creating a logger."""
        logger = StructuredLogger("test", LogLevel.DEBUG)
        assert logger.name == "test"
        
    def test_get_logger_singleton(self):
        """Test get_logger returns cached instance."""
        logger1 = get_logger("singleton-test")
        logger2 = get_logger("singleton-test")
        assert logger1 is logger2


# =============================================================================
# TRACER TESTS
# =============================================================================
class TestSpan:
    """Tests for Span dataclass."""
    
    def test_duration_calculation(self):
        """Test span duration calculation."""
        span = Span(span_id="s1", trace_id="t1", name="test")
        span.end()
        assert span.duration_ms is not None
        assert span.duration_ms >= 0
        
    def test_add_event(self):
        """Test adding events to span."""
        span = Span(span_id="s1", trace_id="t1", name="test")
        span.add_event("test_event", {"key": "value"})
        assert len(span.events) == 1
        assert span.events[0]["name"] == "test_event"
        
    def test_set_error(self):
        """Test setting error on span."""
        span = Span(span_id="s1", trace_id="t1", name="test")
        span.set_error("TestError", "Something went wrong")
        assert span.status == SpanStatus.ERROR
        assert span.error["type"] == "TestError"
        
    def test_to_dict(self):
        """Test converting span to dict."""
        span = Span(span_id="s1", trace_id="t1", name="test")
        d = span.to_dict()
        assert d["span_id"] == "s1"
        assert d["trace_id"] == "t1"


class TestTracer:
    """Tests for Tracer class."""
    
    def test_start_trace(self):
        """Test starting a new trace."""
        tracer = Tracer()
        span = tracer.start_trace("request")
        assert span.trace_id is not None
        assert span.parent_span_id is None
        
    def test_start_child_span(self):
        """Test starting a child span."""
        tracer = Tracer()
        parent = tracer.start_trace("parent")
        child = tracer.start_span("child")
        assert child.parent_span_id == parent.span_id
        assert child.trace_id == parent.trace_id
        
    def test_get_trace_spans(self):
        """Test getting all spans for a trace."""
        tracer = Tracer()
        span = tracer.start_trace("test")
        tracer.start_span("child1")
        tracer.start_span("child2")
        spans = tracer.get_trace_spans(span.trace_id)
        assert len(spans) == 3
        
    def test_trace_context_manager(self):
        """Test trace context manager."""
        tracer = Tracer()
        tracer.start_trace("test")
        
        with trace_context(tracer, "operation") as span:
            assert span.status == SpanStatus.RUNNING
            
        assert span.status == SpanStatus.SUCCESS
        
    def test_trace_context_manager_error(self):
        """Test trace context manager with error."""
        tracer = Tracer()
        tracer.start_trace("test")
        
        with pytest.raises(ValueError):
            with trace_context(tracer, "operation") as span:
                raise ValueError("Test error")
                
        assert span.status == SpanStatus.ERROR


class TestGlobalTracer:
    """Tests for global tracer instance."""
    
    def test_get_tracer_returns_instance(self):
        """Test get_tracer returns a Tracer."""
        tracer = get_tracer()
        assert isinstance(tracer, Tracer)


# =============================================================================
# TIMELINE TESTS
# =============================================================================
class TestTimelineEvent:
    """Tests for TimelineEvent dataclass."""
    
    def test_to_dict(self):
        """Test converting event to dict."""
        event = TimelineEvent(
            event_type=EventType.TASK_RECEIVED,
            phase="INTAKE",
            message="Test",
        )
        d = event.to_dict()
        assert d["event_type"] == "task_received"
        assert d["phase"] == "INTAKE"


class TestExecutionTimeline:
    """Tests for ExecutionTimeline class."""
    
    def test_add_event(self):
        """Test adding events to timeline."""
        timeline = ExecutionTimeline(trace_id="t1")
        event = timeline.add_event(EventType.TASK_RECEIVED, message="Test")
        assert len(timeline.events) == 1
        assert event.event_type == EventType.TASK_RECEIVED
        
    def test_record_task_received(self):
        """Test recording task received."""
        timeline = ExecutionTimeline(trace_id="t1")
        event = timeline.record_task_received("Write a function to...")
        assert event.event_type == EventType.TASK_RECEIVED
        assert "task_preview" in event.data
        
    def test_record_selection(self):
        """Test recording selection events."""
        timeline = ExecutionTimeline(trace_id="t1")
        timeline.record_selection_start(["claude", "gemini"])
        timeline.record_selection_complete("claude", 1200.0, "Best for coding")
        assert len(timeline.events) == 2
        
    def test_finalize(self):
        """Test finalizing timeline."""
        timeline = ExecutionTimeline(trace_id="t1")
        timeline.add_event(EventType.TASK_RECEIVED)
        timeline.finalize()
        assert timeline.end_time is not None
        assert timeline.total_duration_ms is not None
        
    def test_to_summary(self):
        """Test getting timeline summary."""
        timeline = ExecutionTimeline(trace_id="t1")
        timeline.record_selection_complete("claude", 1000.0)
        timeline.record_execution_complete("claude", 2000.0)
        summary = timeline.to_summary()
        assert len(summary) == 2


class TestTimelineManager:
    """Tests for TimelineManager class."""
    
    def test_create_timeline(self):
        """Test creating timeline."""
        manager = TimelineManager()
        timeline = manager.create_timeline("t1")
        assert timeline.trace_id == "t1"
        
    def test_get_timeline(self):
        """Test getting timeline."""
        manager = TimelineManager()
        manager.create_timeline("t1")
        timeline = manager.get_timeline("t1")
        assert timeline is not None
        
    def test_max_timelines(self):
        """Test timeline eviction at capacity."""
        manager = TimelineManager(max_timelines=2)
        manager.create_timeline("t1")
        manager.create_timeline("t2")
        manager.create_timeline("t3")
        assert manager.get_timeline("t1") is None
        assert manager.get_timeline("t3") is not None


# =============================================================================
# ERROR TRACKER TESTS
# =============================================================================
class TestErrorClassification:
    """Tests for ErrorClassification enum."""
    
    def test_from_timeout_exception(self):
        """Test classifying timeout exception."""
        class TimeoutError(Exception):
            pass
        exc = TimeoutError("Request timed out")
        classification = ErrorClassification.from_exception(exc)
        assert classification == ErrorClassification.TIMEOUT
        
    def test_from_unknown_exception(self):
        """Test classifying unknown exception."""
        exc = Exception("Unknown error")
        classification = ErrorClassification.from_exception(exc)
        assert classification == ErrorClassification.UNKNOWN


class TestErrorRecord:
    """Tests for ErrorRecord dataclass."""
    
    def test_to_dict(self):
        """Test converting error to dict."""
        record = ErrorRecord(
            error_id="err_123",
            trace_id="t1",
            error_type="ValueError",
            message="Invalid input",
            classification=ErrorClassification.VALIDATION_ERROR,
        )
        d = record.to_dict()
        assert d["error_id"] == "err_123"
        assert d["classification"] == "validation_error"


class TestErrorTracker:
    """Tests for ErrorTracker class."""
    
    def test_record_error(self):
        """Test recording an error."""
        tracker = ErrorTracker()
        record = tracker.record_error(
            trace_id="t1",
            error_type="TestError",
            message="Test error message",
        )
        assert record.error_id.startswith("err_")
        assert record.trace_id == "t1"
        
    def test_record_exception(self):
        """Test recording from exception."""
        tracker = ErrorTracker()
        exc = ValueError("Invalid value")
        record = tracker.record_exception("t1", exc)
        assert record.error_type == "ValueError"
        assert record.stack_trace is not None
        
    def test_get_recent_errors(self):
        """Test getting recent errors."""
        tracker = ErrorTracker()
        tracker.record_error("t1", "E1", "Error 1")
        tracker.record_error("t2", "E2", "Error 2")
        errors = tracker.get_recent_errors(limit=1)
        assert len(errors) == 1
        assert errors[0].message == "Error 2"
        
    def test_get_errors_by_trace(self):
        """Test getting errors by trace ID."""
        tracker = ErrorTracker()
        tracker.record_error("t1", "E1", "Error 1")
        tracker.record_error("t1", "E2", "Error 2")
        tracker.record_error("t2", "E3", "Error 3")
        errors = tracker.get_errors_by_trace("t1")
        assert len(errors) == 2
        
    def test_error_stats(self):
        """Test getting error stats."""
        tracker = ErrorTracker()
        tracker.record_error("t1", "TimeoutError", "Timed out",
                           classification=ErrorClassification.TIMEOUT)
        tracker.record_error("t2", "APIError", "API failed",
                           classification=ErrorClassification.API_ERROR)
        stats = tracker.get_error_stats()
        assert stats["total_errors"] == 2
        assert "timeout" in stats["by_classification"]
        
    def test_clear(self):
        """Test clearing errors."""
        tracker = ErrorTracker()
        tracker.record_error("t1", "E1", "Error")
        tracker.clear()
        assert len(tracker.get_recent_errors()) == 0


class TestGlobalErrorTracker:
    """Tests for global error tracker instance."""
    
    def test_get_error_tracker_returns_instance(self):
        """Test get_error_tracker returns an ErrorTracker."""
        tracker = get_error_tracker()
        assert isinstance(tracker, ErrorTracker)
