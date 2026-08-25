from __future__ import annotations

import asyncio
from typing import Annotated

from emc_core.domain.workspace import WorkspaceEntry, WorkspaceInfo
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field

from emc_backend.composition import AppContainer
from emc_backend.dependencies import get_container
from emc_backend.os_dialog import pick_directory

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


class WorkspaceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    name: str
    current: bool


class WorkspaceListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current: WorkspaceResponse
    items: list[WorkspaceResponse]


class SelectWorkspaceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1, max_length=4096)


class WorkspaceEntryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    path: str
    kind: str
    children: list[WorkspaceEntryResponse]


def _workspace_response(workspace: WorkspaceInfo) -> WorkspaceResponse:
    return WorkspaceResponse(
        path=workspace.path,
        name=workspace.name,
        current=workspace.current,
    )


def _entry_response(entry: WorkspaceEntry) -> WorkspaceEntryResponse:
    return WorkspaceEntryResponse(
        name=entry.name,
        path=entry.path,
        kind=entry.kind,
        children=[_entry_response(child) for child in entry.children],
    )


@router.get("", response_model=WorkspaceListResponse)
async def list_workspaces(
    container: Annotated[AppContainer, Depends(get_container)],
) -> WorkspaceListResponse:
    items = await container.workspace_service.list()
    current = next(item for item in items if item.current)
    return WorkspaceListResponse(
        current=_workspace_response(current),
        items=[_workspace_response(item) for item in items],
    )


@router.post("/select", response_model=WorkspaceResponse)
async def select_workspace(
    payload: SelectWorkspaceRequest,
    container: Annotated[AppContainer, Depends(get_container)],
) -> WorkspaceResponse:
    try:
        selected = await container.workspace_service.select(payload.path)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    return _workspace_response(selected)


@router.post(
    "/pick",
    response_model=WorkspaceResponse,
    responses={status.HTTP_204_NO_CONTENT: {"description": "用户取消选择"}},
)
async def pick_workspace(
    request: Request,
    container: Annotated[AppContainer, Depends(get_container)],
) -> WorkspaceResponse | Response:
    """打开本机系统目录选择器并切换工作区。"""

    client_host = request.client.host if request.client else ""
    if client_host not in {"127.0.0.1", "::1", "testclient"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="系统目录选择器只允许本机调用",
        )
    current = await container.workspace_service.current()
    try:
        selected_path = await asyncio.to_thread(pick_directory, current.path)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    if selected_path is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    try:
        selected = await container.workspace_service.select(selected_path)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return _workspace_response(selected)


@router.get("/tree", response_model=list[WorkspaceEntryResponse])
async def workspace_tree(
    container: Annotated[AppContainer, Depends(get_container)],
    depth: Annotated[int, Query(ge=1, le=4)] = 2,
) -> list[WorkspaceEntryResponse]:
    entries = await container.workspace_service.tree(depth=depth)
    return [_entry_response(entry) for entry in entries]
