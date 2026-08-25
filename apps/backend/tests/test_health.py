from __future__ import annotations

from pathlib import Path
from typing import Any

from emc_backend.composition import AppContainer
from emc_backend.config import Settings
from emc_backend.main import create_app
from fastapi.testclient import TestClient


class FakeRuntime:
    """健康接口只读取类型名，因此测试不需要启动真实 Agent loop。"""


class FakeContainer(AppContainer):
    def __init__(self, settings: Settings) -> None:
        # FakeContainer 覆盖所有被测试路径，不创建 Ollama AsyncClient。
        self.settings = settings
        self.runtime = FakeRuntime()  # type: ignore[assignment]
        self.started = False
        self.closed = False

    async def start(self) -> None:
        self.started = True

    async def close(self) -> None:
        self.closed = True

    async def ollama_status(self) -> dict[str, Any]:
        return {
            "available": True,
            "host": self.settings.ollama_host,
            "models": [self.settings.chat_model, self.settings.embedding_model],
            "chat_model": self.settings.chat_model,
            "embedding_model": self.settings.embedding_model,
            "chat_model_installed": True,
            "embedding_model_installed": True,
        }


def _settings() -> Settings:
    return Settings(project_root=Path.cwd())


def test_health_reports_runtime_and_ollama_status() -> None:
    container = FakeContainer(_settings())
    application = create_app(
        settings=container.settings,
        container_factory=lambda _: container,
    )

    with TestClient(application) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "emc-backend",
        "environment": "development",
        "runtime": "FakeRuntime",
        "ollama": {
            "available": True,
            "host": "http://127.0.0.1:11434",
            "models": ["qwen3.5:9b-q4_K_M", "nomic-embed-text"],
            "chat_model": "qwen3.5:9b-q4_K_M",
            "embedding_model": "nomic-embed-text",
            "chat_model_installed": True,
            "embedding_model_installed": True,
        },
    }
    assert container.started is True
    assert container.closed is True


def test_models_endpoint_separates_chat_and_embedding_roles() -> None:
    container = FakeContainer(_settings())
    application = create_app(
        settings=container.settings,
        container_factory=lambda _: container,
    )

    with TestClient(application) as client:
        response = client.get("/api/v1/models")

    assert response.status_code == 200
    assert response.json()["configured"] == [
        {"name": "qwen3.5:9b-q4_K_M", "role": "chat", "installed": True},
        {"name": "nomic-embed-text", "role": "embedding", "installed": True},
    ]
    assert response.json()["default_chat_model"] == "qwen3.5:9b-q4_K_M"
    assert response.json()["chat_candidates"] == ["qwen3.5:9b-q4_K_M"]


def test_models_endpoint_excludes_latest_tagged_embedding_model() -> None:
    container = FakeContainer(_settings())

    async def latest_tag_status() -> dict[str, Any]:
        status = await FakeContainer.ollama_status(container)
        status["models"] = ["nomic-embed-text:latest", "qwen3.5:9b-q4_K_M"]
        return status

    container.ollama_status = latest_tag_status  # type: ignore[method-assign]
    application = create_app(
        settings=container.settings,
        container_factory=lambda _: container,
    )

    with TestClient(application) as client:
        response = client.get("/api/v1/models")

    assert response.status_code == 200
    assert response.json()["chat_candidates"] == ["qwen3.5:9b-q4_K_M"]


def test_openapi_metadata_and_routes_are_available() -> None:
    container = FakeContainer(_settings())
    application = create_app(
        settings=container.settings,
        container_factory=lambda _: container,
    )

    with TestClient(application) as client:
        document = client.get("/openapi.json").json()

    assert document["info"]["title"] == "EMC Fault Probe Agent API"
    assert "/api/v1/health" in document["paths"]
    assert "/api/v1/models" in document["paths"]
    assert "/api/v1/sessions" in document["paths"]


def test_built_web_workbench_is_served_from_root(tmp_path: Path) -> None:
    web_dist = tmp_path / "apps" / "web" / "dist"
    web_dist.mkdir(parents=True)
    web_dist.joinpath("index.html").write_text("<h1>EMC workbench</h1>", encoding="utf-8")
    settings = Settings(project_root=tmp_path)
    container = FakeContainer(settings)
    application = create_app(settings=settings, container_factory=lambda _: container)

    with TestClient(application) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "EMC workbench" in response.text
