from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any
from uuid import uuid4

from emc_core.ports.llm import ChatMessage, LLMOutput
from emc_core.tools.models import ToolCall, ToolSpec
from ollama import AsyncClient, ChatResponse


def _tool_spec_to_ollama(
    tool_spec: ToolSpec,
) -> dict[str, Any]:
    """
    把项目内部的 ToolSpec 转换成 Ollama tools 格式。

    项目内部格式：

    ToolSpec(
        name="search_cases",
        description="查询故障案例",
        parameters={...},
    )

    Ollama 格式：

    {
        "type": "function",
        "function": {
            "name": "search_cases",
            "description": "查询故障案例",
            "parameters": {...},
        },
    }
    """

    return {
        "type": "function",
        "function": {
            "name": tool_spec.name,
            "description": tool_spec.description,
            # deepcopy 会递归复制整个 JSON Schema。
            #
            # 如果后面的 SDK 修改了这份字典，
            # 不会影响 ToolRegistry 中保存的原始 ToolSpec。
            "parameters": deepcopy(tool_spec.parameters),
        },
    }


def _normalize_arguments(
    raw_arguments: Any,
) -> dict[str, Any]:
    """
    把 Ollama 返回的工具参数统一转换成 dict。

    Ollama 0.6.x 一般返回 Mapping；
    这里也兼容某些版本返回 JSON 字符串的情况。
    """

    if isinstance(raw_arguments, str):
        raw_arguments = json.loads(raw_arguments)

    if not isinstance(raw_arguments, Mapping):
        raise TypeError("Ollama tool arguments 必须是 JSON object。")

    # dict(...) 创建一份普通字典副本。
    #
    # Mapping 是只读接口类型，而 ToolCall.arguments
    # 明确要求 dict[str, Any]。
    return dict(raw_arguments)


def _message_to_ollama(
    message: ChatMessage,
) -> dict[str, Any]:
    """
    把 Runtime 内部消息转换成 Ollama 消息。

    普通 system/user/assistant 消息可以直接转换。

    Runtime 内部使用单数 tool_call：

    {
        "role": "assistant",
        "tool_call": {
            "name": "search_cases",
            "arguments": {...},
            "call_id": "...",
        },
    }

    Ollama 使用复数 tool_calls：

    {
        "role": "assistant",
        "tool_calls": [
            {
                "function": {
                    "name": "search_cases",
                    "arguments": {...},
                },
            }
        ],
    }
    """

    role = message.get("role")

    if not isinstance(role, str):
        raise ValueError("消息缺少有效的 role 字段。")

    raw_content = message.get("content")

    ollama_message: dict[str, Any] = {
        "role": role,
        "content": ("" if raw_content is None else str(raw_content)),
    }

    if role == "assistant":
        internal_tool_call = message.get("tool_call")

        if internal_tool_call is not None:
            if not isinstance(internal_tool_call, Mapping):
                raise TypeError("assistant.tool_call 必须是 object。")

            tool_name = internal_tool_call.get("name")
            arguments = internal_tool_call.get(
                "arguments",
                {},
            )

            if not isinstance(tool_name, str):
                raise ValueError("assistant.tool_call 缺少工具名称。")

            if not isinstance(arguments, Mapping):
                raise TypeError("assistant.tool_call.arguments 必须是 object。")

            ollama_message["tool_calls"] = [
                {
                    "function": {
                        "name": tool_name,
                        "arguments": dict(arguments),
                    }
                }
            ]

    if role == "tool":
        tool_name = message.get("tool_name")

        if not isinstance(tool_name, str):
            raise ValueError("tool 消息缺少有效的 tool_name。")

        ollama_message["tool_name"] = tool_name

        # 当前 Ollama API 不使用 OpenAI 风格的 tool_call_id。
        # Runtime 内部仍然保留 call_id，供事件追踪使用，
        # 但发送给 Ollama 时不需要传递。

    return ollama_message


class OllamaLLM:
    """
    emc_core.ports.llm.LLM 的 Ollama 实现。

    这个类不需要显式继承 LLM。

    因为 LLM 是 Protocol，只要 OllamaLLM 提供签名兼容的
    complete() 方法，就可以被 run_loop() 当作 LLM 使用。
    这叫作结构化类型或静态鸭子类型。
    """

    def __init__(
        self,
        *,
        model: str,
        host: str | None = None,
        think: bool = True,
        options: Mapping[str, Any] | None = None,
        client: AsyncClient | None = None,
    ) -> None:
        """
        创建 Ollama Adapter。

        client 参数用于依赖注入：

        - 正式运行时不传，自动创建 AsyncClient
        - 测试时可以传入假的 Client
        """

        self._model = model
        self._think = think
        self._owns_client = client is None

        # options 可能是 None，所以使用 options or {}。
        # dict(...) 同时创建副本，防止外部代码之后修改原字典。
        self._options = dict(options or {})

        # 如果调用方传入 client，就使用它；
        # 否则创建真正的 Ollama AsyncClient。
        self._client = client if client is not None else AsyncClient(host=host)

    async def close(self) -> None:
        """关闭由本 Adapter 自己创建的 AsyncClient。"""

        # composition 注入的共享 Client 可能同时供 Chat 和 Embedding 使用，
        # 因此 Adapter 不能擅自关闭不属于自己的资源。
        if self._owns_client:
            await self._client.close()

    async def complete(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[ToolSpec],
    ) -> LLMOutput:
        """
        调用一次 Ollama。

        返回值只可能是：

        - str：模型已经给出最终回答
        - ToolCall：模型要求 Runtime 执行工具
        """

        ollama_messages = [_message_to_ollama(message) for message in messages]

        ollama_tools = [_tool_spec_to_ollama(tool_spec) for tool_spec in tools]

        # await 表示暂停当前协程，等待 Ollama HTTP 请求完成。
        #
        # 暂停期间事件循环可以处理其他任务，
        # 不会像普通同步 HTTP 请求一样阻塞整个程序。
        response = await self._client.chat(
            model=self._model,
            messages=ollama_messages,
            tools=ollama_tools or None,
            stream=False,
            think=self._think,
            options=self._options,
        )

        # stream=False 时应该返回 ChatResponse。
        # 这个检查可以在 SDK 行为异常时尽早暴露问题。
        if not isinstance(response, ChatResponse):
            raise TypeError("Ollama stream=False 时应返回 ChatResponse。")

        assistant_message = response.message
        native_tool_calls = list(assistant_message.tool_calls or [])

        if not native_tool_calls:
            return assistant_message.content or ""

        # 当前 LLMOutput 和 run_loop 每轮只支持一个 ToolCall。
        # 显式报错比静默丢弃第二个调用更安全。
        if len(native_tool_calls) > 1:
            raise RuntimeError(
                "当前 Agent Loop 每轮只支持一个工具调用，"
                f"Ollama 本轮返回了 {len(native_tool_calls)} 个。"
            )

        native_tool_call = native_tool_calls[0]
        function = native_tool_call.function

        return ToolCall(
            name=function.name,
            arguments=_normalize_arguments(
                function.arguments,
            ),
            # Ollama 当前没有提供稳定的 tool call ID，
            # 所以在适配器边界生成一个内部 ID。
            #
            # uuid4().hex 会返回随机的 32 位十六进制字符串。
            call_id=f"ollama-{uuid4().hex}",
        )
