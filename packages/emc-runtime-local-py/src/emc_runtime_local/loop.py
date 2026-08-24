from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from typing import Any

from emc_core.agent.state import AgentState
from emc_core.domain.events import AgentEvent, AgentEventType
from emc_core.ports.llm import LLM
from emc_core.tools.models import ToolCall, ToolResult, ToolSpec

ToolExecutor = Callable[
    [ToolCall],
    Awaitable[ToolResult],
]


def _tool_result_content(result: ToolResult) -> str:
    """把工具结果转换成可以回填给模型的文本"""

    if result.error is not None:
        return f"[工具执行错误] {result.error}"

    if result.output is None:
        return ""

    return str(result.output)


def _tool_call_data(tool_call: ToolCall) -> dict[str, Any]:
    """把 ToolCall 转换成事件数据"""

    return {
        "tool_name": tool_call.name,
        "call_id": tool_call.call_id,
        "arguments": tool_call.arguments,
    }


async def run_loop(
    *,
    state: AgentState,
    llm: LLM,
    tools: Sequence[ToolSpec],
    execute_tool: ToolExecutor | None,
    max_steps: int = 5,
) -> AsyncIterator[AgentEvent]:
    """执行最小的 model → tool → model Agent loop。"""

    if max_steps < 1:
        raise ValueError("max_steps must be greater than 0")

    # 使用 yield 字段，当会话开始的时候暂停并返回值
    yield AgentEvent(
        type=AgentEventType.TURN_STARTED,
        session_id=state.session_id,
        step=state.step,
    )

    while state.step < max_steps:
        # 回话被用户取消的情况处理
        if state.cancelled:
            yield AgentEvent(
                type=AgentEventType.TURN_FAILED,
                session_id=state.session_id,
                step=state.step,
                data={
                    "reason": "cancelled",
                },
            )
            return

        state.step += 1

        response = await llm.complete(
            messages=state.messages,
            tools=tools,
        )

        if isinstance(response, str):
            state.messages.append(
                {
                    "role": "assistant",
                    "content": response,
                }
            )

            yield AgentEvent(
                type=AgentEventType.ASSISTANT_COMPLETED,
                session_id=state.session_id,
                step=state.step,
                data={
                    "content": response,
                },
            )

            yield AgentEvent(
                type=AgentEventType.TURN_COMPLETED,
                session_id=state.session_id,
                step=state.step,
                data={
                    "content": response,
                },
            )
            return

        tool_call = response
        state.pending_tool_call = tool_call

        yield AgentEvent(
            type=AgentEventType.TOOL_REQUESTED,
            session_id=state.session_id,
            step=state.step,
            data=_tool_call_data(tool_call),
        )

        # 记录模型刚刚发出的工具调用。
        # 当前使用的是 Runtime 内部的统一消息格式，
        # 以后由 Ollama Adapter 转换成 Ollama 原生格式。
        state.messages.append(
            {
                "role": "assistant",
                "content": "",
                "tool_call": {
                    "name": tool_call.name,
                    "arguments": tool_call.arguments,
                    "call_id": tool_call.call_id,
                },
            }
        )

        if execute_tool is None:
            tool_result = ToolResult(
                tool_name=tool_call.name,
                call_id=tool_call.call_id,
                error="No tool executor was provided.",
            )
        else:
            try:
                tool_result = await execute_tool(tool_call)
            except Exception as exc:  # noqa: BLE001
                # 工具可能来自第三方；统一转成 ToolResult，避免中断 Agent loop。
                tool_result = ToolResult(
                    tool_name=tool_call.name,
                    call_id=tool_call.call_id,
                    error=f"{type(exc).__name__}: {exc}",
                )

        result_content = _tool_result_content(tool_result)

        state.messages.append(
            {
                "role": "tool",
                "tool_name": tool_call.name,
                "call_id": tool_call.call_id,
                "content": result_content,
            }
        )

        yield AgentEvent(
            type=AgentEventType.TOOL_COMPLETED,
            session_id=state.session_id,
            step=state.step,
            data={
                "tool_name": tool_result.tool_name,
                "call_id": tool_result.call_id,
                "output": tool_result.output,
                "error": tool_result.error,
            },
        )

        state.pending_tool_call = None

    yield AgentEvent(
        type=AgentEventType.TURN_FAILED,
        session_id=state.session_id,
        step=state.step,
        data={
            "reason": "max_steps_exceeded",
            "max_steps": max_steps,
        },
    )
