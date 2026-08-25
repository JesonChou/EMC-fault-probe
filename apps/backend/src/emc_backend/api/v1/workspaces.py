from __future__ import annotations

from typing import Annotated

from emc_core.domain.workspace import WorkspaceEntry, WorkspaceInfo
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from emc_backend.composition import AppContainer
from emc_backend.dependencies import get_container

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


@router.get("/tree", response_model=list[WorkspaceEntryResponse])
async def workspace_tree(
    container: Annotated[AppContainer, Depends(get_container)],
    depth: Annotated[int, Query(ge=1, le=4)] = 2,
) -> list[WorkspaceEntryResponse]:
    entries = await container.workspace_service.tree(depth=depth)
    return [_entry_response(entry) for entry in entries]
