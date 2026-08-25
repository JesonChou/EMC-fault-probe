from __future__ import annotations

from pathlib import Path

from emc_backend.composition import AppContainer
from emc_backend.config import Settings
from emc_backend.main import create_app
from emc_core.application.workspace_service import WorkspaceService
from emc_core.workspace.manager import WorkspaceManager
from emc_core.workspace.recent_store import RecentWorkspaceStore
from fastapi.testclient import TestClient


class WorkspaceApiContainer(AppContainer):
    def __init__(self, settings: Settings, state_path: Path) -> None:
        self.settings = settings
        self.workspace_service = WorkspaceService(
            WorkspaceManager(
                default_path=settings.project_root,
                store=RecentWorkspaceStore(state_path),
            )
        )

    async def start(self) -> None:
        return None

    async def close(self) -> None:
        return None


def test_workspace_api_selects_directory_and_returns_tree(tmp_path: Path) -> None:
    project = tmp_path / "project"
    (project / "apps" / "web").mkdir(parents=True)
    (project / "README.md").write_text("# demo", encoding="utf-8")
    selected = tmp_path / "selected"
    (selected / "src").mkdir(parents=True)
    (selected / "src" / "main.py").write_text("", encoding="utf-8")
    settings = Settings(project_root=project)
    container = WorkspaceApiContainer(settings, tmp_path / "state" / "recent.json")
    application = create_app(settings=settings, container_factory=lambda _: container)

    with TestClient(application) as client:
        initial = client.get("/api/v1/workspaces")
        changed = client.post("/api/v1/workspaces/select", json={"path": str(selected)})
        tree = client.get("/api/v1/workspaces/tree", params={"depth": 2})

    assert initial.status_code == 200
    assert initial.json()["current"]["path"] == str(project.resolve())
    assert changed.status_code == 200
    assert changed.json() == {
        "path": str(selected.resolve()),
        "name": "selected",
        "current": True,
    }
    assert tree.json()[0]["name"] == "src"
    assert tree.json()[0]["children"][0]["name"] == "main.py"


def test_workspace_api_rejects_missing_directory(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    settings = Settings(project_root=project)
    container = WorkspaceApiContainer(settings, tmp_path / "recent.json")
    application = create_app(settings=settings, container_factory=lambda _: container)

    with TestClient(application) as client:
        response = client.post(
            "/api/v1/workspaces/select",
            json={"path": str(tmp_path / "missing")},
        )

    assert response.status_code == 422
    assert "工作区不存在" in response.json()["detail"]


def test_workspace_api_picks_directory_with_native_dialog(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project = tmp_path / "project"
    selected = tmp_path / "selected"
    project.mkdir()
    selected.mkdir()
    settings = Settings(project_root=project)
    container = WorkspaceApiContainer(settings, tmp_path / "recent.json")
    application = create_app(settings=settings, container_factory=lambda _: container)
    monkeypatch.setattr(
        "emc_backend.api.v1.workspaces.pick_directory",
        lambda _initial: str(selected),
    )

    with TestClient(application) as client:
        response = client.post("/api/v1/workspaces/pick")

    assert response.status_code == 200
    assert response.json()["path"] == str(selected.resolve())


def test_workspace_api_returns_no_content_when_picker_is_cancelled(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    settings = Settings(project_root=project)
    container = WorkspaceApiContainer(settings, tmp_path / "recent.json")
    application = create_app(settings=settings, container_factory=lambda _: container)
    monkeypatch.setattr(
        "emc_backend.api.v1.workspaces.pick_directory",
        lambda _initial: None,
    )

    with TestClient(application) as client:
        response = client.post("/api/v1/workspaces/pick")

    assert response.status_code == 204
