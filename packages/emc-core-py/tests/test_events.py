from dataclasses import FrozenInstanceError

import pytest
from emc_core.domain.events import AgentEvent, AgentEventType


def test_event_types_use_stable_wire_names() -> None:
    assert AgentEventType.TURN_STARTED.value == "turn.started"
    assert AgentEventType.TOOL_REQUESTED.value == "tool.requested"
    assert AgentEventType.TOOL_COMPLETED.value == "tool.completed"
    assert AgentEventType.ASSISTANT_COMPLETED.value == "assistant.completed"
    assert AgentEventType.TURN_COMPLETED.value == "turn.completed"
    assert AgentEventType.TURN_FAILED.value == "turn.failed"


def test_event_can_be_created_without_data() -> None:
    event = AgentEvent(
        type=AgentEventType.TURN_STARTED,
        session_id="session-001",
        step=0,
    )

    assert event.type is AgentEventType.TURN_STARTED
    assert event.session_id == "session-001"
    assert event.step == 0
    assert event.data == {}


def test_event_stores_tool_call_data() -> None:
    event = AgentEvent(
        type=AgentEventType.TOOL_REQUESTED,
        session_id="session-001",
        step=1,
        data={
            "tool_name": "search_cases",
            "call_id": "call-001",
            "arguments": {
                "query": "辐射发射超标",
            },
        },
    )

    assert event.type is AgentEventType.TOOL_REQUESTED
    assert event.data["tool_name"] == "search_cases"
    assert event.data["call_id"] == "call-001"
    assert event.data["arguments"]["query"] == "辐射发射超标"


def test_each_event_gets_an_independent_data_dict() -> None:
    first = AgentEvent(
        type=AgentEventType.TURN_STARTED,
        session_id="session-001",
        step=0,
    )
    second = AgentEvent(
        type=AgentEventType.TURN_STARTED,
        session_id="session-002",
        step=0,
    )

    first.data["source"] = "test"

    assert first.data["source"] == "test"
    assert second.data == {}


def test_event_is_immutable() -> None:
    event = AgentEvent(
        type=AgentEventType.TURN_STARTED,
        session_id="session-001",
        step=0,
    )

    with pytest.raises(FrozenInstanceError):
        setattr(event, "step", 1)  # noqa: B010 - intentionally tests frozen dataclass
