from emc_core.agent.state import AgentState
from emc_core.tools.models import ToolCall


def test_agent_state_has_expected_defaults() -> None:
    state = AgentState(session_id="session-001")

    assert state.session_id == "session-001"
    assert state.messages == []
    assert state.step == 0
    assert state.cancelled is False
    assert state.pending_tool_call is None


def test_agent_state_can_track_message_and_step_progress() -> None:
    state = AgentState(session_id="session-001")

    state.messages.append(
        {
            "role": "user",
            "content": "查询辐射发射超标案例",
        }
    )
    state.step += 1

    assert state.messages == [
        {
            "role": "user",
            "content": "查询辐射发射超标案例",
        }
    ]
    assert state.step == 1


def test_agent_state_can_track_cancellation() -> None:
    state = AgentState(session_id="session-001")

    state.cancelled = True

    assert state.cancelled is True


def test_agent_state_can_track_and_clear_pending_tool_call() -> None:
    state = AgentState(session_id="session-001")
    tool_call = ToolCall(
        name="search_cases",
        arguments={"query": "辐射发射超标"},
        call_id="call-001",
    )

    state.pending_tool_call = tool_call

    assert state.pending_tool_call is tool_call
    assert state.pending_tool_call.name == "search_cases"

    state.pending_tool_call = None

    assert state.pending_tool_call is None


def test_agent_states_do_not_share_messages() -> None:
    first = AgentState(session_id="session-001")
    second = AgentState(session_id="session-002")

    first.messages.append({"role": "user", "content": "第一条消息"})

    assert first.messages != second.messages
    assert second.messages == []
