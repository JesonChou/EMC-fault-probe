from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ToolSpec:
    """给模型看的工具描述。"""

    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ToolCall:
    """模型请求执行一次工具调用。"""

    name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    call_id: str | None = None


@dataclass(frozen=True, slots=True)
class ToolResult:
    """工具执行后返回给 Runtime 和模型的结果。"""

    tool_name: str
    output: Any = None
    call_id: str | None = None
    error: str | None = None
