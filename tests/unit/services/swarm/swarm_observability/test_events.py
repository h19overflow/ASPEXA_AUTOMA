"""Tests for swarm_observability events module."""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from services.swarm.swarm_observability.events import (
    EventType,
    StreamEvent,
    create_event,
    safe_get_stream_writer,
)


class TestEventType:
    """Tests for EventType enum."""

    def test_lifecycle_events_exist(self):
        """Verify all lifecycle event types are defined."""
        assert EventType.SCAN_STARTED == "scan_started"
        assert EventType.SCAN_PAUSED == "scan_paused"
        assert EventType.SCAN_RESUMED == "scan_resumed"
        assert EventType.SCAN_CANCELLED == "scan_cancelled"
        assert EventType.SCAN_COMPLETE == "scan_complete"
        assert EventType.SCAN_ERROR == "scan_error"

    def test_node_events_exist(self):
        """Verify all node event types are defined."""
        assert EventType.NODE_ENTER == "node_enter"
        assert EventType.NODE_PROGRESS == "node_progress"
        assert EventType.NODE_EXIT == "node_exit"

    def test_planning_events_exist(self):
        """Verify all planning event types are defined."""
        assert EventType.PLAN_START == "plan_start"
        assert EventType.PLAN_COMPLETE == "plan_complete"

    def test_execution_events_exist(self):
        """Verify all execution event types are defined."""
        assert EventType.PROBE_START == "probe_start"
        assert EventType.PROBE_RESULT == "probe_result"
        assert EventType.PROBE_COMPLETE == "probe_complete"

    def test_agent_events_exist(self):
        """Verify all agent event types are defined."""
        assert EventType.AGENT_START == "agent_start"
        assert EventType.AGENT_COMPLETE == "agent_complete"

    def test_system_events_exist(self):
        """Verify all system event types are defined."""
        assert EventType.LOG == "log"
        assert EventType.HEARTBEAT == "heartbeat"

    def test_event_type_is_string_enum(self):
        """EventType should be usable as a string."""
        event_type = EventType.SCAN_STARTED
        assert isinstance(event_type, str)
        assert event_type == "scan_started"


class TestStreamEvent:
    """Tests for StreamEvent model."""

    def test_create_minimal_event(self):
        """Create event with only required field."""
        event = StreamEvent(type=EventType.SCAN_STARTED)

        assert event.type == EventType.SCAN_STARTED
        assert isinstance(event.timestamp, datetime)
        assert event.node is None
        assert event.agent is None
        assert event.message is None
        assert event.data is None
        assert event.progress is None

    def test_create_full_event(self):
        """Create event with all fields populated."""
        timestamp = datetime(2024, 1, 15, 10, 30, 0)
        event = StreamEvent(
            type=EventType.NODE_PROGRESS,
            timestamp=timestamp,
            node="execute_probes",
            agent="sql_injection",
            message="Processing SQL injection probes",
            data={"probes_completed": 5, "total_probes": 10},
            progress=0.5,
        )

        assert event.type == EventType.NODE_PROGRESS
        assert event.timestamp == timestamp
        assert event.node == "execute_probes"
        assert event.agent == "sql_injection"
        assert event.message == "Processing SQL injection probes"
        assert event.data == {"probes_completed": 5, "total_probes": 10}
        assert event.progress == 0.5

    def test_timestamp_auto_generated(self):
        """Timestamp should be auto-generated if not provided."""
        before = datetime.now(UTC)
        event = StreamEvent(type=EventType.HEARTBEAT)
        after = datetime.now(UTC)

        assert before <= event.timestamp <= after

    def test_progress_validation_min(self):
        """Progress should not be less than 0."""
        with pytest.raises(ValueError):
            StreamEvent(type=EventType.NODE_PROGRESS, progress=-0.1)

    def test_progress_validation_max(self):
        """Progress should not be greater than 1."""
        with pytest.raises(ValueError):
            StreamEvent(type=EventType.NODE_PROGRESS, progress=1.1)

    def test_progress_boundary_values(self):
        """Progress should accept boundary values 0 and 1."""
        event_start = StreamEvent(type=EventType.NODE_PROGRESS, progress=0.0)
        event_end = StreamEvent(type=EventType.NODE_PROGRESS, progress=1.0)

        assert event_start.progress == 0.0
        assert event_end.progress == 1.0

    def test_json_serialization(self):
        """Event should serialize to JSON properly."""
        event = StreamEvent(
            type=EventType.SCAN_COMPLETE,
            message="Scan finished",
            data={"results": 42},
        )

        json_dict = event.model_dump()

        assert json_dict["type"] == "scan_complete"
        assert json_dict["message"] == "Scan finished"
        assert json_dict["data"] == {"results": 42}


class TestCreateEvent:
    """Tests for create_event factory function."""

    def test_create_simple_event(self):
        """Create event using factory function."""
        event = create_event(EventType.SCAN_STARTED)

        assert event.type == EventType.SCAN_STARTED
        assert isinstance(event.timestamp, datetime)

    def test_create_event_with_all_params(self):
        """Create event with all optional parameters."""
        event = create_event(
            EventType.PROBE_RESULT,
            node="execute_probes",
            agent="auth_bypass",
            message="Probe completed",
            data={"vulnerable": True},
            progress=0.75,
        )

        assert event.type == EventType.PROBE_RESULT
        assert event.node == "execute_probes"
        assert event.agent == "auth_bypass"
        assert event.message == "Probe completed"
        assert event.data == {"vulnerable": True}
        assert event.progress == 0.75

    def test_factory_returns_stream_event(self):
        """Factory should return StreamEvent instance."""
        event = create_event(EventType.LOG, message="Test log")

        assert isinstance(event, StreamEvent)


class TestSafeGetStreamWriter:
    """Tests for safe_get_stream_writer function."""

    def test_returns_callable(self):
        """safe_get_stream_writer should return a callable."""
        writer = safe_get_stream_writer()
        assert callable(writer)

    def test_no_op_when_outside_langgraph_context(self):
        """Should return no-op writer when outside LangGraph context."""
        # By default, we're outside LangGraph context in unit tests
        writer = safe_get_stream_writer()

        # Should not raise when called with event data
        event = {"type": "test", "data": "value"}
        result = writer(event)
        assert result is None  # No-op function returns None

    def test_handles_runtime_error_from_get_stream_writer(self):
        """Should catch RuntimeError and return no-op writer."""
        with patch('langgraph.config.get_stream_writer') as mock_get:
            # Simulate RuntimeError when get_stream_writer is called
            mock_get.side_effect = RuntimeError("Not in LangGraph context")

            writer = safe_get_stream_writer()
            assert callable(writer)

            # Should be able to call it without error
            result = writer({"type": "test"})
            assert result is None

    def test_handles_import_error(self):
        """Should catch ImportError and return no-op writer."""
        with patch('langgraph.config.get_stream_writer') as mock_get:
            # Simulate ImportError when get_stream_writer is called
            mock_get.side_effect = ImportError("langgraph not available")

            writer = safe_get_stream_writer()
            assert callable(writer)

            result = writer({"type": "test"})
            assert result is None

    def test_writer_accepts_any_dict(self):
        """Writer should accept dictionaries of any structure."""
        writer = safe_get_stream_writer()

        # Test with various event structures
        events = [
            {"type": "scan_started"},
            {"type": "node_enter", "node": "execute", "agent": "sql"},
            {"type": "probe_result", "data": {"vulnerable": True}, "progress": 0.5},
            {"type": "error", "message": "Test error", "meta": {"key": "value"}},
        ]

        for event in events:
            result = writer(event)
            assert result is None  # No-op should always return None

    def test_multiple_calls_to_safe_get_stream_writer(self):
        """Multiple calls should return independent callables."""
        writer1 = safe_get_stream_writer()
        writer2 = safe_get_stream_writer()

        # Both should be callable
        assert callable(writer1)
        assert callable(writer2)

        # Both should work
        assert writer1({"type": "test"}) is None
        assert writer2({"type": "test"}) is None
