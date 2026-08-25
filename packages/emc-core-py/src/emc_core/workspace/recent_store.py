from __future__ import annotations

import json
from pathlib import Path


class RecentWorkspaceStore:
    """保存本地当前工作区和最近目录，写入采用同目录原子替换。"""

    def __init__(self, path: Path, *, limit: int = 8) -> None:
        self._path = path.resolve()
        self._limit = limit

    def load(self) -> tuple[str | None, list[str]]:
        if not self._path.is_file():
            return None, []
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None, []
        if not isinstance(payload, dict):
            return None, []
        current = payload.get("current")
        recent = payload.get("recent")
        return (
            str(current) if isinstance(current, str) and current else None,
            [str(item) for item in recent if isinstance(item, str)]
            if isinstance(recent, list)
            else [],
        )

    def select(self, path: Path) -> None:
        current, recent = self.load()
        normalized = str(path.resolve())
        ordered = [normalized, *(item for item in recent if item != normalized)]
        if current and current != normalized and current not in ordered:
            ordered.append(current)
        payload = {"current": normalized, "recent": ordered[: self._limit]}
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_suffix(self._path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self._path)
