from __future__ import annotations

from datetime import datetime
from typing import Any

from emc_core.domain.session import Session, SessionMessage, SessionSummary
from pydantic import BaseModel, Field


class SessionSummaryResponse(BaseModel):
    session_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    turns: int
    workspace_path: str | None


class SessionMessageResponse(BaseModel):
    message_id: str
    role: str
    content: str
    thinking: str | None
    metadata: dict[str, Any]
    created_at: datetime


class SessionResponse(BaseModel):
    session_id: str
    created_at: datetime
    workspace_path: str | None
    messages: list[SessionMessageResponse]


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=20_000)
    model: str | None = Field(default=None, min_length=1, max_length=300)
    think: bool | None = None
    workspace_path: str | None = Field(default=None, min_length=1, max_length=4096)


class CancelResponse(BaseModel):
    cancelled: bool


def summary_response(summary: SessionSummary) -> SessionSummaryResponse:
    return SessionSummaryResponse(
        session_id=summary.session_id,
        title=summary.title,
        created_at=summary.created_at,
        updated_at=summary.updated_at,
        turns=summary.turns,
        workspace_path=summary.workspace_path,
    )


def message_response(message: SessionMessage) -> SessionMessageResponse:
    return SessionMessageResponse(
        message_id=message.message_id,
        role=message.role.value,
        content=message.content,
        thinking=message.thinking,
        metadata=message.metadata,
        created_at=message.created_at,
    )


def session_response(session: Session) -> SessionResponse:
    return SessionResponse(
        session_id=session.session_id,
        created_at=session.created_at,
        workspace_path=session.workspace_path,
        messages=[message_response(message) for message in session.messages],
    )
