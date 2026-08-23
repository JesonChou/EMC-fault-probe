from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class AgentEventType(StrEnum):
    """Agent Runtime 对外产生的事件类型。"""

    TURN_STARTED = "turn.started"
    TOOL_REQUESTED = "tool.requested"
    TOOL_COMPLETED = "tool.completed"
    ASSISTANT_COMPLETED = "assistant.completed"
    TURN_COMPLETED = "turn.completed"
    TURN_FAILED = "turn.failed"


@dataclass(frozen=True, slots=True)
class AgentEvent:
    """Agent Runtime 对外产生的统一事件。"""

    type: AgentEventType
    session_id: str
    step: int
    data: dict[str, Any] = field(default_factory=dict)
