from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

from emc_core.agent.state import AgentState
from emc_core.application.chat_service import ChatService
from emc_core.domain.events import AgentEvent, AgentEventType
from emc_core.persistence.jsonl_store import JsonlSessionStore


class FakeStreamingRuntime:
    def __init__(self) -> None:
        self.states: list[AgentState] = []

    async def run(self, *, state: AgentState) -> AsyncIterator[AgentEvent]:
        self.states.append(state)
        yield AgentEvent(
            type=AgentEventType.TURN_STARTED,
            session_id=state.session_id,
            step=0,
        )
        yield AgentEvent(
            type=AgentEventType.ASSISTANT_THINKING_DELTA,
            session_id=state.session_id,
            step=1,
            data={"delta": "内部思考"},
        )
        yield AgentEvent(
            type=AgentEventType.ASSISTANT_CONTENT_DELTA,
            session_id=state.session_id,
            step=1,
            data={"delta": "正式回答"},
        )
        yield AgentEvent(
            type=AgentEventType.ASSISTANT_COMPLETED,
            session_id=state.session_id,
            step=1,
            data={"content": "正式回答"},
        )
        yield AgentEvent(
            type=AgentEventType.TURN_COMPLETED,
            session_id=state.session_id,
            step=1,
            data={"content": "正式回答"},
        )


async def _collect(stream: AsyncIterator[AgentEvent]) -> list[AgentEvent]:
    return [event async for event in stream]


def test_chat_service_persists_thinking_but_excludes_it_from_model_history(
    tmp_path: Path,
) -> None:
    store = JsonlSessionStore(tmp_path)
    session = store.create()
    runtime = FakeStreamingRuntime()
    service = ChatService(
        store=store,
        runtime=runtime,
        system_prompt="系统提示",
    )

    first_events = asyncio.run(
        _collect(service.send_message(session_id=session.session_id, content="第一问"))
    )
    second_events = asyncio.run(
        _collect(service.send_message(session_id=session.session_id, content="第二问"))
    )

    assert first_events[-1].type is AgentEventType.TURN_COMPLETED
    assert second_events[-1].type is AgentEventType.TURN_COMPLETED
    restored = store.load(session.session_id)
    assert restored.messages[1].thinking == "内部思考"
    second_history = runtime.states[1].messages
    assert second_history == [
        {"role": "system", "content": "系统提示"},
        {"role": "user", "content": "第一问"},
        {"role": "assistant", "content": "正式回答"},
        {"role": "user", "content": "第二问"},
    ]
    assert all("内部思考" not in message["content"] for message in second_history)


def test_chat_service_resolves_per_turn_runtime_and_workspace_context(
    tmp_path: Path,
) -> None:
    store = JsonlSessionStore(tmp_path)
    session = store.create()
    default_runtime = FakeStreamingRuntime()
    selected_runtime = FakeStreamingRuntime()
    requests: list[tuple[str | None, bool | None]] = []

    def runtime_factory(model: str | None, think: bool | None) -> FakeStreamingRuntime:
        requests.append((model, think))
        return selected_runtime

    service = ChatService(
        store=store,
        runtime=default_runtime,
        runtime_factory=runtime_factory,
        system_prompt="系统提示",
    )
    asyncio.run(
        _collect(
            service.send_message(
                session_id=session.session_id,
                content="分析当前项目",
                model="qwen-custom:latest",
                think=False,
                workspace_path=str(tmp_path),
            )
        )
    )

    assert requests == [("qwen-custom:latest", False)]
    assert selected_runtime.states[0].messages[:2] == [
        {"role": "system", "content": "系统提示"},
        {"role": "system", "content": f"当前用户选择的本地工作区是：{tmp_path}"},
    ]
    restored = store.load(session.session_id)
    assert restored.messages[0].metadata == {
        "model": "qwen-custom:latest",
        "think": False,
        "workspace_path": str(tmp_path),
    }
