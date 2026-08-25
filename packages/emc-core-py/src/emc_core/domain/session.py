from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from emc_core.domain.events import AgentEvent


def utc_now() -> datetime:
    """返回带 UTC 时区的当前时间，避免跨时区排序出现歧义。"""

    return datetime.now(UTC)


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


@dataclass(frozen=True, slots=True)
class SessionMessage:
    """持久化消息；thinking 和 metadata 不会默认回放给模型。"""

    role: MessageRole
    content: str
    created_at: datetime = field(default_factory=utc_now)
    message_id: str = field(default_factory=lambda: uuid4().hex)
    thinking: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_llm_message(self) -> dict[str, str]:
        """只输出模型历史需要的 role/content。"""

        return {"role": self.role.value, "content": self.content}


@dataclass(frozen=True, slots=True)
class SessionSummary:
    session_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    turns: int
    workspace_path: str | None = None


@dataclass(slots=True)
class Session:
    session_id: str
    created_at: datetime
    messages: list[SessionMessage] = field(default_factory=list)
    events: list[AgentEvent] = field(default_factory=list)

    @property
    def workspace_path(self) -> str | None:
        """Return the workspace that the first contextualized turn bound to."""

        for message in self.messages:
            value = message.metadata.get("workspace_path")
            if message.role is MessageRole.USER and isinstance(value, str) and value:
                return value
        return None

    @property
    def summary(self) -> SessionSummary:
        user_messages = [m for m in self.messages if m.role is MessageRole.USER]
        title = user_messages[0].content[:30] if user_messages else "新会话"
        updated_at = (
            max(message.created_at for message in self.messages)
            if self.messages
            else self.created_at
        )
        return SessionSummary(
            session_id=self.session_id,
            title=title,
            created_at=self.created_at,
            updated_at=updated_at,
            turns=len(user_messages),
            workspace_path=self.workspace_path,
        )
