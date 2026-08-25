from __future__ import annotations

from pathlib import Path

IGNORED_WORKSPACE_NAMES = {
    ".git",
    ".idea",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "dist",
    "node_modules",
}


def resolve_workspace_path(value: str | Path) -> Path:
    raw = str(value).strip()
    if not raw:
        raise ValueError("工作区路径不能为空")
    path = Path(raw).expanduser().resolve()
    if not path.exists():
        raise ValueError(f"工作区不存在：{path}")
    if not path.is_dir():
        raise ValueError(f"工作区必须是目录：{path}")
    return path


def is_visible_workspace_entry(path: Path) -> bool:
    return path.name not in IGNORED_WORKSPACE_NAMES and not path.name.startswith(".")
