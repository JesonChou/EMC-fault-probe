from __future__ import annotations

from pathlib import Path

import pytest
from emc_backend.config import Settings, discover_project_root


def test_settings_read_and_normalize_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    project_root = Path.cwd()
    monkeypatch.setenv("EMC_PROJECT_ROOT", str(project_root))
    monkeypatch.setenv("EMC_BACKEND_PORT", "8123")
    monkeypatch.setenv("EMC_AUTO_START_OLLAMA", "yes")
    monkeypatch.setenv("EMC_OLLAMA_HOST", "http://localhost:11434/")
    monkeypatch.setenv("EMC_OLLAMA_THINK", "false")
    monkeypatch.setenv("EMC_OLLAMA_NUM_PREDICT", "1024")
    monkeypatch.setenv("EMC_RUNTIME_ROOT", str(project_root / "local-runtime"))

    settings = Settings.from_env()

    assert settings.project_root == project_root.resolve()
    assert settings.port == 8123
    assert settings.auto_start_ollama is True
    assert settings.ollama_host == "http://localhost:11434"
    assert settings.ollama_think is False
    assert settings.ollama_num_predict == 1024
    assert settings.chroma_path == project_root / "local-runtime" / "vector_store"
    assert settings.session_path == project_root / "local-runtime" / "sessions"
    assert (
        settings.ollama_log_path
        == project_root / "local-runtime" / "logs" / "ollama_serve.log"
    )


def test_invalid_boolean_configuration_fails_early(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EMC_PROJECT_ROOT", str(Path.cwd()))
    monkeypatch.setenv("EMC_AUTO_START_OLLAMA", "sometimes")

    with pytest.raises(ValueError, match="EMC_AUTO_START_OLLAMA"):
        Settings.from_env()


def test_project_root_is_discovered_from_nested_directory() -> None:
    nested_file = Path.cwd() / "apps" / "backend" / "src" / "emc_backend" / "main.py"

    assert discover_project_root(nested_file) == Path.cwd().resolve()
