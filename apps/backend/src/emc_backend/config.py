from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env_bool(name: str, default: bool) -> bool:
    """读取布尔环境变量，并在拼写错误时尽早失败。

    环境变量只有字符串类型，因此不能写 ``bool(os.getenv(...))``：
    Python 中任何非空字符串都为真，连字符串 ``"false"`` 也会变成 True。
    显式映射能避免这一类难以发现的配置错误。
    """

    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False

    raise ValueError(f"{name} 必须是 true/false，当前值：{raw_value!r}")


def _env_int(name: str, default: int) -> int:
    """读取整数环境变量，并提供包含变量名的错误信息。"""

    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} 必须是整数，当前值：{raw_value!r}") from exc


def discover_project_root(start: Path | None = None) -> Path:
    """从当前目录和模块目录向上寻找仓库根目录。

    使用 ``Path`` 而不是手工拼接反斜杠，使同一份代码可以运行在 Windows、
    Linux 和 CI。候选目录必须同时包含 ``data`` 与 ``packages``，避免误把
    apps/backend 自己的 ``pyproject.toml`` 当作仓库根目录。
    """

    configured_root = os.getenv("EMC_PROJECT_ROOT")
    if configured_root:
        return Path(configured_root).expanduser().resolve()

    candidates: list[Path] = []
    for origin in (start or Path.cwd(), Path(__file__).resolve()):
        resolved = origin.resolve()
        directory = resolved if resolved.is_dir() else resolved.parent
        candidates.extend((directory, *directory.parents))

    for candidate in candidates:
        if (candidate / "data").is_dir() and (candidate / "packages").is_dir():
            return candidate

    raise RuntimeError(
        "无法定位项目根目录；请设置 EMC_PROJECT_ROOT 指向仓库根目录。"
    )


@dataclass(frozen=True, slots=True)
class Settings:
    """后端不可变配置。

    ``frozen=True`` 防止运行期间意外修改配置；``slots=True`` 可阻止拼错属性名
    时静默创建新属性。二者都适合承载启动后不应变化的应用设置。
    """

    project_root: Path
    runtime_root: Path | None = None
    environment: str = "development"
    host: str = "127.0.0.1"
    port: int = 8000
    ollama_host: str = "http://127.0.0.1:11434"
    chat_model: str = "qwen3.5:9b-q4_K_M"
    embedding_model: str = "nomic-embed-text"
    ollama_think: bool = True
    ollama_num_predict: int = 2048
    auto_start_ollama: bool = False
    max_agent_steps: int = 5
    chroma_collection: str = "emc_faults"

    @property
    def chroma_path(self) -> Path:
        """返回由正式数据脚本构建的本地向量库路径。"""

        return (self.runtime_root or self.project_root / "data" / "runtime") / "vector_store"

    @property
    def session_path(self) -> Path:
        """返回 JSONL 会话目录；开发版和打包版使用同一相对位置。"""

        return (self.runtime_root or self.project_root / "data" / "runtime") / "sessions"

    @property
    def workspace_state_path(self) -> Path:
        return (
            (self.runtime_root or self.project_root / "data" / "runtime")
            / "workspaces"
            / "recent.json"
        )

    @property
    def system_prompt_path(self) -> Path:
        return (
            self.project_root
            / "packages"
            / "emc-runtime-local-py"
            / "prompts"
            / "system.md"
        )

    @property
    def ollama_log_path(self) -> Path:
        """返回由后端启动 Ollama 时使用的日志路径。"""

        runtime_directory = self.runtime_root or self.project_root / "data" / "runtime"
        return runtime_directory / "logs" / "ollama_serve.log"

    @classmethod
    def from_env(cls) -> Settings:
        """从环境变量构造配置，是正式应用唯一的环境读取入口。"""

        port = _env_int("EMC_BACKEND_PORT", 8000)
        max_steps = _env_int("EMC_MAX_AGENT_STEPS", 5)
        num_predict = _env_int("EMC_OLLAMA_NUM_PREDICT", 2048)
        runtime_root_value = os.getenv("EMC_RUNTIME_ROOT")
        runtime_root = (
            Path(runtime_root_value).expanduser().resolve()
            if runtime_root_value
            else None
        )
        if not 1 <= port <= 65535:
            raise ValueError("EMC_BACKEND_PORT 必须在 1 到 65535 之间")
        if max_steps < 1:
            raise ValueError("EMC_MAX_AGENT_STEPS 必须大于 0")
        if num_predict < 1:
            raise ValueError("EMC_OLLAMA_NUM_PREDICT 必须大于 0")

        return cls(
            project_root=discover_project_root(),
            runtime_root=runtime_root,
            environment=os.getenv("EMC_ENVIRONMENT", "development"),
            host=os.getenv("EMC_BACKEND_HOST", "127.0.0.1"),
            port=port,
            ollama_host=os.getenv(
                "EMC_OLLAMA_HOST",
                "http://127.0.0.1:11434",
            ).rstrip("/"),
            chat_model=os.getenv("EMC_OLLAMA_MODEL", "qwen3.5:9b-q4_K_M"),
            embedding_model=os.getenv(
                "EMC_EMBEDDING_MODEL",
                "nomic-embed-text",
            ),
            ollama_think=_env_bool("EMC_OLLAMA_THINK", True),
            ollama_num_predict=num_predict,
            auto_start_ollama=_env_bool("EMC_AUTO_START_OLLAMA", False),
            max_agent_steps=max_steps,
            chroma_collection=os.getenv("EMC_CHROMA_COLLECTION", "emc_faults"),
        )
