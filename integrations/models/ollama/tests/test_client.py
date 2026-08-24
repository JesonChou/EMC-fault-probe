from __future__ import annotations

import asyncio
from typing import Any

from emc_core.tools.models import ToolCall, ToolSpec
from ollama import ChatResponse

from integrations.models.ollama.client import OllamaLLM, _message_to_ollama


class FakeOllamaClient:
    """只实现 OllamaLLM 实际需要的 chat() 方法。"""

    def __init__(self, response: ChatResponse) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    async def chat(self, **kwargs: Any) -> ChatResponse:
        self.calls.append(kwargs)
        return self.response


def test_ollama_llm_returns_text_answer() -> None:
    client = FakeOllamaClient(
        ChatResponse(
            message={"role": "assistant", "content": "最终回答"},
        )
    )
    llm = OllamaLLM(model="fake-model", client=client)  # type: ignore[arg-type]

    output = asyncio.run(
        llm.complete(
            messages=[{"role": "user", "content": "你好"}],
            tools=[],
        )
    )

    assert output == "最终回答"
    assert client.calls[0]["model"] == "fake-model"


def test_ollama_llm_converts_native_tool_call() -> None:
    client = FakeOllamaClient(
        ChatResponse(
            message={
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "search_cases",
                            "arguments": {"query": "辐射发射超标"},
                        }
                    }
                ],
            },
        )
    )
    llm = OllamaLLM(model="fake-model", client=client)  # type: ignore[arg-type]

    output = asyncio.run(
        llm.complete(
            messages=[{"role": "user", "content": "查询案例"}],
            tools=[ToolSpec(name="search_cases", description="查询案例")],
        )
    )

    assert isinstance(output, ToolCall)
    assert output.name == "search_cases"
    assert output.arguments == {"query": "辐射发射超标"}
    assert output.call_id is not None


def test_internal_tool_message_is_converted_back_to_ollama() -> None:
    message = _message_to_ollama(
        {
            "role": "assistant",
            "content": "",
            "tool_call": {
                "name": "search_cases",
                "arguments": {"query": "传导发射"},
                "call_id": "internal-call-id",
            },
        }
    )

    assert message["tool_calls"] == [
        {
            "function": {
                "name": "search_cases",
                "arguments": {"query": "传导发射"},
            }
        }
    ]
