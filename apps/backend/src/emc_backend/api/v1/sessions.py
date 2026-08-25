from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Annotated

from emc_core.application.chat_service import SessionBusyError
from emc_core.persistence.jsonl_store import SessionNotFoundError
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from emc_backend.api.v1.schemas import (
    CancelResponse,
    SendMessageRequest,
    SessionResponse,
    SessionSummaryResponse,
    session_response,
    summary_response,
)
from emc_backend.composition import AppContainer
from emc_backend.dependencies import get_container

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    container: Annotated[AppContainer, Depends(get_container)],
) -> SessionResponse:
    return session_response(await container.session_service.create())


@router.get("", response_model=list[SessionSummaryResponse])
async def list_sessions(
    container: Annotated[AppContainer, Depends(get_container)],
) -> list[SessionSummaryResponse]:
    summaries = await container.session_service.list()
    return [summary_response(summary) for summary in summaries]


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    container: Annotated[AppContainer, Depends(get_container)],
) -> SessionResponse:
    try:
        session = await container.session_service.get(session_id)
    except (SessionNotFoundError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    return session_response(session)


@router.post("/{session_id}/messages")
async def send_message(
    session_id: str,
    payload: SendMessageRequest,
    request: Request,
    container: Annotated[AppContainer, Depends(get_container)],
) -> StreamingResponse:
    """把一轮 AgentEvent 编码成浏览器和桌面端都能消费的 SSE。"""

    try:
        await container.session_service.get(session_id)
    except (SessionNotFoundError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    if container.chat_service.is_active(session_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(SessionBusyError(f"会话正在运行：{session_id}")),
        )

    try:
        await container.validate_chat_model(payload.model)
        workspace_path = None
        if payload.workspace_path is not None:
            selected = await container.workspace_service.select(payload.workspace_path)
            workspace_path = selected.path
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    async def event_stream() -> AsyncIterator[str]:
        try:
            async for event in container.chat_service.send_message(
                session_id=session_id,
                content=payload.content,
                model=payload.model,
                think=payload.think,
                workspace_path=workspace_path,
            ):
                if await request.is_disconnected():
                    container.chat_service.cancel(session_id)
                    return
                wire_event = {
                    "type": event.type.value,
                    "session_id": event.session_id,
                    "step": event.step,
                    "data": event.data,
                }
                yield f"data: {json.dumps(wire_event, ensure_ascii=False)}\n\n"
        except Exception as exc:  # noqa: BLE001 - SSE 已发送响应头，只能用事件报告错误
            # StreamingResponse 开始后已经不能改成 HTTP 500。把运行时异常编码成
            # 统一 turn.failed 事件，桌面端就能结束 loading 并显示可诊断信息。
            wire_event = {
                "type": "turn.failed",
                "session_id": session_id,
                "step": 0,
                "data": {"reason": f"{type(exc).__name__}: {exc}"},
            }
            yield f"data: {json.dumps(wire_event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{session_id}/cancel", response_model=CancelResponse)
async def cancel_turn(
    session_id: str,
    container: Annotated[AppContainer, Depends(get_container)],
) -> CancelResponse:
    return CancelResponse(cancelled=container.chat_service.cancel(session_id))
