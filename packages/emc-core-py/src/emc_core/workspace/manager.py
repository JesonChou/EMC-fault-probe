from __future__ import annotations

from pathlib import Path

from emc_core.domain.workspace import WorkspaceEntry, WorkspaceInfo
from emc_core.workspace.path_policy import (
    is_visible_workspace_entry,
    resolve_workspace_path,
)
from emc_core.workspace.recent_store import RecentWorkspaceStore


class WorkspaceManager:
    def __init__(self, *, default_path: Path, store: RecentWorkspaceStore) -> None:
        self._default = resolve_workspace_path(default_path)
        self._store = store

    def list(self) -> list[WorkspaceInfo]:
        stored_current, recent = self._store.load()
        current = self._existing_directory(stored_current) or self._default
        paths = [current, self._default]
        paths.extend(
            path
            for value in recent
            if (path := self._existing_directory(value)) is not None
        )
        unique: list[Path] = []
        seen: set[str] = set()
        for path in paths:
            key = str(path).casefold()
            if key not in seen:
                seen.add(key)
                unique.append(path)
        return [
            WorkspaceInfo(path=str(path), name=path.name, current=path == current)
            for path in unique
        ]

    def select(self, value: str | Path) -> WorkspaceInfo:
        path = resolve_workspace_path(value)
        self._store.select(path)
        return WorkspaceInfo(path=str(path), name=path.name, current=True)

    def current(self) -> WorkspaceInfo:
        return next(item for item in self.list() if item.current)

    def tree(self, *, depth: int = 2, max_entries: int = 300) -> list[WorkspaceEntry]:
        if depth < 1 or depth > 4:
            raise ValueError("工作区树深度必须在 1 到 4 之间")
        remaining = [max_entries]
        return list(self._entries(Path(self.current().path), "", depth, remaining))

    def _entries(
        self,
        directory: Path,
        relative_parent: str,
        depth: int,
        remaining: list[int],
    ) -> tuple[WorkspaceEntry, ...]:
        if remaining[0] <= 0:
            return ()
        try:
            children = sorted(
                (
                    path
                    for path in directory.iterdir()
                    if is_visible_workspace_entry(path)
                ),
                key=lambda path: (not path.is_dir(), path.name.casefold()),
            )
        except OSError:
            return ()
        output: list[WorkspaceEntry] = []
        for path in children:
            if remaining[0] <= 0:
                break
            remaining[0] -= 1
            relative = f"{relative_parent}/{path.name}".lstrip("/")
            kind = "directory" if path.is_dir() else "file"
            nested = (
                self._entries(path, relative, depth - 1, remaining)
                if kind == "directory" and depth > 1 and not path.is_symlink()
                else ()
            )
            output.append(
                WorkspaceEntry(
                    name=path.name, path=relative, kind=kind, children=nested
                )
            )
        return tuple(output)

    @staticmethod
    def _existing_directory(value: str | None) -> Path | None:
        if not value:
            return None
        try:
            return resolve_workspace_path(value)
        except ValueError:
            return None
