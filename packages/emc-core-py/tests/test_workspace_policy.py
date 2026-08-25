from pathlib import Path

import pytest
from emc_core.workspace.manager import WorkspaceManager
from emc_core.workspace.path_policy import resolve_workspace_path
from emc_core.workspace.recent_store import RecentWorkspaceStore


def test_workspace_manager_selects_recent_directory_and_builds_bounded_tree(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    (project / "apps" / "web").mkdir(parents=True)
    (project / "apps" / "web" / "main.tsx").write_text("", encoding="utf-8")
    (project / "node_modules").mkdir()
    other = tmp_path / "other"
    other.mkdir()
    manager = WorkspaceManager(
        default_path=project,
        store=RecentWorkspaceStore(tmp_path / "runtime" / "recent.json"),
    )

    assert manager.current().path == str(project.resolve())
    manager.select(other)
    listed = manager.list()
    assert listed[0].path == str(other.resolve())
    assert listed[0].current is True

    manager.select(project)
    tree = manager.tree(depth=3)
    assert [entry.name for entry in tree] == ["apps"]
    assert tree[0].children[0].children[0].name == "main.tsx"


def test_workspace_path_rejects_missing_paths_and_files(tmp_path: Path) -> None:
    file_path = tmp_path / "not-a-directory.txt"
    file_path.write_text("x", encoding="utf-8")

    with pytest.raises(ValueError, match="不存在"):
        resolve_workspace_path(tmp_path / "missing")
    with pytest.raises(ValueError, match="必须是目录"):
        resolve_workspace_path(file_path)
