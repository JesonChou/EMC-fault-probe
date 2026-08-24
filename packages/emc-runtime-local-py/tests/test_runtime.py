from __future__ import annotations

import asyncio
from collections.abc import Sequence

from emc_core.agent.state import AgentState
from emc_core.domain.events import AgentEventType
from emc_core.ports.llm import ChatMessage, LLMOutput
from emc_core.tools.models import ToolCall, ToolResult, ToolSpec
from emc_core.tools.registry import ToolRegistry
from emc_runtime_local.loop import run_loop
from emc_runtime_local.runtime import LocalRuntime


class FakeLLM:
    """按预设顺序返回文本或工具调用。"""

    def __init__(self, *responses: LLMOutput) -> None:
        self.responses = list(responses)
        self.calls: list[
            tuple[
                Sequence[ChatMessage],
                Sequence[ToolSpec],
            ]
        ] = []

    async def complete(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[ToolSpec],
    ) -> LLMOutput:
        self.calls.append((list(messages), list(tools)))

        if not self.responses:
            raise AssertionError("FakeLLM 没有预设更多响应")

        return self.responses.pop(0)


async def collect_events(event_stream):
    return [event async for event in event_stream]


def test_runtime_can_return_direct_answer() -> None:
    state = AgentState(
        session_id="session-001",
        messages=[
            {
                "role": "user",
                "content": "你是什么模型？",
            }
        ],
    )

    llm = FakeLLM("这是 FakeLLM 的直接回答。")

    events = asyncio.run(
        collect_events(
            run_loop(
                state=state,
                llm=llm,
                tools=[],
                execute_tool=None,
            )
        )
    )

    assert [event.type for event in events] == [
        AgentEventType.TURN_STARTED,
        AgentEventType.ASSISTANT_COMPLETED,
        AgentEventType.TURN_COMPLETED,
    ]

    assert state.messages[-1] == {
        "role": "assistant",
        "content": "这是 FakeLLM 的直接回答。",
    }

    assert len(llm.calls) == 1


def test_runtime_can_execute_one_tool_then_answer() -> None:
    state = AgentState(
        session_id="session-002",
        messages=[
            {
                "role": "user",
                "content": "查询辐射发射超标案例。",
            }
        ],
    )

    llm = FakeLLM(
        ToolCall(
            name="search_cases",
            arguments={
                "query": "辐射发射超标",
            },
            call_id="call-001",
        ),
        "根据查询结果，建议检查滤波器和接地结构。",
    )

    executed_calls: list[ToolCall] = []

    async def execute_tool(tool_call: ToolCall) -> ToolResult:
        executed_calls.append(tool_call)

        return ToolResult(
            tool_name=tool_call.name,
            call_id=tool_call.call_id,
            output="查询到 3 条相关案例。",
        )

    events = asyncio.run(
        collect_events(
            run_loop(
                state=state,
                llm=llm,
                tools=[
                    ToolSpec(
                        name="search_cases",
                        description="查询 EMC 故障案例。",
                        parameters={
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                },
                            },
                            "required": ["query"],
                        },
                    )
                ],
                execute_tool=execute_tool,
            )
        )
    )

    assert [event.type for event in events] == [
        AgentEventType.TURN_STARTED,
        AgentEventType.TOOL_REQUESTED,
        AgentEventType.TOOL_COMPLETED,
        AgentEventType.ASSISTANT_COMPLETED,
        AgentEventType.TURN_COMPLETED,
    ]

    assert len(llm.calls) == 2
    assert len(executed_calls) == 1
    assert executed_calls[0].name == "search_cases"
    assert state.pending_tool_call is None
    assert state.messages[-1] == {
        "role": "assistant",
        "content": "根据查询结果，建议检查滤波器和接地结构。",
    }

    second_call_messages, _ = llm.calls[1]
    assert second_call_messages[-1] == {
        "role": "tool",
        "tool_name": "search_cases",
        "call_id": "call-001",
        "content": "查询到 3 条相关案例。",
    }


def test_runtime_stops_when_cancelled() -> None:
    state = AgentState(
        session_id="session-cancelled",
        messages=[{"role": "user", "content": "继续诊断。"}],
        cancelled=True,
    )
    llm = FakeLLM("不应该调用模型。")

    events = asyncio.run(
        collect_events(
            run_loop(
                state=state,
                llm=llm,
                tools=[],
                execute_tool=None,
            )
        )
    )

    assert [event.type for event in events] == [
        AgentEventType.TURN_STARTED,
        AgentEventType.TURN_FAILED,
    ]
    assert events[-1].data == {"reason": "cancelled"}
    assert llm.calls == []
    assert state.step == 0


def test_runtime_fails_after_reaching_max_steps() -> None:
    state = AgentState(
        session_id="session-max-steps",
        messages=[{"role": "user", "content": "连续查询案例。"}],
    )
    llm = FakeLLM(
        ToolCall(
            name="search_cases",
            arguments={"query": "传导发射超标"},
            call_id="call-max-001",
        )
    )

    async def execute_tool(tool_call: ToolCall) -> ToolResult:
        return ToolResult(
            tool_name=tool_call.name,
            call_id=tool_call.call_id,
            output="查询完成。",
        )

    events = asyncio.run(
        collect_events(
            run_loop(
                state=state,
                llm=llm,
                tools=[],
                execute_tool=execute_tool,
                max_steps=1,
            )
        )
    )

    assert [event.type for event in events] == [
        AgentEventType.TURN_STARTED,
        AgentEventType.TOOL_REQUESTED,
        AgentEventType.TOOL_COMPLETED,
        AgentEventType.TURN_FAILED,
    ]
    assert events[-1].data == {
        "reason": "max_steps_exceeded",
        "max_steps": 1,
    }
    assert state.pending_tool_call is None
    assert state.step == 1


def test_runtime_returns_tool_exception_to_model() -> None:
    state = AgentState(
        session_id="session-tool-error",
        messages=[{"role": "user", "content": "查询故障案例。"}],
    )
    llm = FakeLLM(
        ToolCall(
            name="search_cases",
            arguments={"query": "辐射抗扰度"},
            call_id="call-error-001",
        ),
        "工具执行失败，请稍后重试。",
    )

    async def execute_tool(_tool_call: ToolCall) -> ToolResult:
        raise RuntimeError("数据库暂时不可用")

    events = asyncio.run(
        collect_events(
            run_loop(
                state=state,
                llm=llm,
                tools=[],
                execute_tool=execute_tool,
            )
        )
    )

    assert [event.type for event in events] == [
        AgentEventType.TURN_STARTED,
        AgentEventType.TOOL_REQUESTED,
        AgentEventType.TOOL_COMPLETED,
        AgentEventType.ASSISTANT_COMPLETED,
        AgentEventType.TURN_COMPLETED,
    ]
    assert events[2].data["error"] == "RuntimeError: 数据库暂时不可用"
    second_call_messages, _ = llm.calls[1]
    assert second_call_messages[-1]["content"] == (
        "[工具执行错误] RuntimeError: 数据库暂时不可用"
    )
    assert state.pending_tool_call is None


def test_local_runtime_composes_llm_registry_and_executor() -> None:
    state = AgentState(
        session_id="session-local-runtime",
        messages=[{"role": "user", "content": "查询辐射发射案例。"}],
    )
    llm = FakeLLM(
        ToolCall(
            name="search_cases",
            arguments={"query": "辐射发射"},
            call_id="call-runtime-001",
        ),
        "已根据工具结果完成回答。",
    )

    async def search_cases(query: str) -> str:
        return f"检索关键词：{query}"

    registry = ToolRegistry()
    registry.register(
        spec=ToolSpec(name="search_cases", description="查询案例"),
        handler=search_cases,
    )
    runtime = LocalRuntime(
        llm=llm,
        registry=registry,
    )

    events = asyncio.run(collect_events(runtime.run(state=state)))

    assert [event.type for event in events] == [
        AgentEventType.TURN_STARTED,
        AgentEventType.TOOL_REQUESTED,
        AgentEventType.TOOL_COMPLETED,
        AgentEventType.ASSISTANT_COMPLETED,
        AgentEventType.TURN_COMPLETED,
    ]
    assert state.messages[-1]["content"] == "已根据工具结果完成回答。"
