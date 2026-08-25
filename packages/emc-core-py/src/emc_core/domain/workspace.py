from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class WorkspaceInfo:
    path: str
    name: str
    current: bool = False


@dataclass(frozen=True, slots=True)
class WorkspaceEntry:
    name: str
    path: str
    kind: str
    children: tuple[WorkspaceEntry, ...] = field(default_factory=tuple)
