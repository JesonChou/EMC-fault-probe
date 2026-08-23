from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol

from emc_core.tools.models import ToolCall, ToolSpec

ChatMessage = Mapping[str, Any]
LLMOutput = str | ToolCall


class LLM(Protocol):
    """Agent Runtime 使用的最小 LLM 接口。"""

    async def complete(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[ToolSpec],
    ) -> LLMOutput:
        """调用模型并返回最终文本或工具调用。"""
        ...
