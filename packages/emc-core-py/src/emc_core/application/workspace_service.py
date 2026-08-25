from __future__ import annotations

import asyncio

from emc_core.domain.workspace import WorkspaceEntry, WorkspaceInfo
from emc_core.workspace.manager import WorkspaceManager


class WorkspaceService:
    def __init__(self, manager: WorkspaceManager) -> None:
        self._manager = manager

    async def list(self) -> list[WorkspaceInfo]:
        return await asyncio.to_thread(self._manager.list)

    async def select(self, path: str) -> WorkspaceInfo:
        return await asyncio.to_thread(self._manager.select, path)

    async def current(self) -> WorkspaceInfo:
        return await asyncio.to_thread(self._manager.current)

    async def tree(self, *, depth: int = 2) -> list[WorkspaceEntry]:
        return await asyncio.to_thread(self._manager.tree, depth=depth)
