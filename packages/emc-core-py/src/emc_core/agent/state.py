from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from emc_core.tools.models import ToolCall


@dataclass(slots=True)
class AgentState:
    """Local Agent Runtime 的当前执行状态。"""

    session_id: str
    messages: list[dict[str, Any]] = field(default_factory=list)
    step: int = 0
    cancelled: bool = False
    pending_tool_call: ToolCall | None = None
