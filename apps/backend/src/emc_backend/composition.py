from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from subprocess import Popen
from typing import Any

from emc_core.application.chat_service import ChatService
from emc_core.application.session_service import SessionService
from emc_core.application.workspace_service import WorkspaceService
from emc_core.persistence.jsonl_store import JsonlSessionStore
from emc_core.ports.agent_runtime import AgentRuntime
from emc_core.tools.registry import ToolRegistry
from emc_core.tools.search_cases import SEARCH_CASES_SPEC, SearchCasesTool
from emc_core.workspace.manager import WorkspaceManager
from emc_core.workspace.recent_store import RecentWorkspaceStore
from emc_runtime_local import LocalRuntime
from ollama import AsyncClient

from emc_backend.config import Settings
from integrations.models.ollama.client import OllamaLLM
from integrations.models.ollama.embeddings import OllamaEmbedder
from integrations.models.ollama.health import (
    ensure_ollama_running,
    is_ollama_model_installed,
    is_ollama_serving,
    list_ollama_models,
    stop_ollama_process,
)
from integrations.vector_stores.chroma.store import ChromaCaseStore, ChromaRetriever


@dataclass(slots=True)
class AppContainer:
    """保存后端生命周期内共享的依赖。

    这里使用显式 dataclass，而不是服务定位器框架。当前依赖数量很少，直接列出
    字段更容易阅读、测试和替换；未来接入成熟 harness 时，只需把 ``runtime``
    换成另一个 ``AgentRuntime`` 实现。
    """

    settings: Settings
    runtime: AgentRuntime
    ollama_client: AsyncClient
    session_service: SessionService
    chat_service: ChatService
    workspace_service: WorkspaceService
    runtime_factory: Callable[[str | None, bool | None], AgentRuntime]
    _ollama_process: Popen[Any] | None = field(default=None, init=False, repr=False)
    _started: bool = field(default=False, init=False, repr=False)
    _closed: bool = field(default=False, init=False, repr=False)

    async def start(self) -> None:
        """启动容器拥有的资源；重复调用不会重复启动服务。"""

        if self._started:
            return
        if self._closed:
            raise RuntimeError("已经关闭的 AppContainer 不能再次启动")

        if self.settings.auto_start_ollama:
            # ensure_ollama_running() 包含同步进程和网络探测，放进工作线程可避免
            # 阻塞 FastAPI 的 asyncio 事件循环。
            self._ollama_process = await asyncio.to_thread(
                ensure_ollama_running,
                host=self.settings.ollama_host,
                log_path=self.settings.ollama_log_path,
            )

        self._started = True

    async def close(self) -> None:
        """按资源所有权关闭客户端和本应用启动的 Ollama 进程。"""

        if self._closed:
            return

        await self.ollama_client.close()

        if self._ollama_process is not None:
            await asyncio.to_thread(stop_ollama_process, self._ollama_process)
            self._ollama_process = None

        self._started = False
        self._closed = True

    async def ollama_status(self) -> dict[str, Any]:
        """返回可供健康接口序列化的 Ollama 状态。"""

        available = await asyncio.to_thread(
            is_ollama_serving,
            host=self.settings.ollama_host,
        )
        models = (
            await asyncio.to_thread(
                list_ollama_models,
                host=self.settings.ollama_host,
            )
            if available
            else []
        )
        return {
            "available": available,
            "host": self.settings.ollama_host,
            "models": models,
            "chat_model": self.settings.chat_model,
            "embedding_model": self.settings.embedding_model,
            "chat_model_installed": is_ollama_model_installed(
                self.settings.chat_model,
                models,
            ),
            "embedding_model_installed": is_ollama_model_installed(
                self.settings.embedding_model,
                models,
            ),
        }

    async def validate_chat_model(self, model: str | None) -> None:
        if model is None:
            return
        normalized = model.strip()
        if not normalized:
            raise ValueError("模型名称不能为空")
        status = await self.ollama_status()
        if normalized not in status["models"]:
            raise ValueError(f"本地未安装模型：{normalized}")


def build_container(settings: Settings) -> AppContainer:
    """创建后端的具体依赖图，不执行网络或磁盘连接。"""

    ollama_client = AsyncClient(host=settings.ollama_host)
    embedder = OllamaEmbedder(
        model=settings.embedding_model,
        client=ollama_client,
    )
    case_store = ChromaCaseStore(
        database_path=settings.chroma_path,
        collection_name=settings.chroma_collection,
    )
    retriever = ChromaRetriever(
        embedder=embedder,
        store=case_store,
    )
    registry = ToolRegistry()
    registry.register(
        spec=SEARCH_CASES_SPEC,
        handler=SearchCasesTool(retriever),
    )

    def runtime_factory(model: str | None, think: bool | None) -> AgentRuntime:
        llm = OllamaLLM(
            model=model or settings.chat_model,
            think=settings.ollama_think if think is None else think,
            # 固定温度让相同故障更稳定地选择相同工具和检索关键词。
            options={
                "temperature": 0,
                "num_predict": settings.ollama_num_predict,
            },
            client=ollama_client,
        )
        return LocalRuntime(
            llm=llm,
            registry=registry,
            max_steps=settings.max_agent_steps,
        )

    runtime = runtime_factory(settings.chat_model, settings.ollama_think)
    session_store = JsonlSessionStore(settings.session_path)
    session_service = SessionService(session_store)
    system_prompt = settings.system_prompt_path.read_text(encoding="utf-8")
    chat_service = ChatService(
        store=session_store,
        runtime=runtime,
        system_prompt=system_prompt,
        runtime_factory=runtime_factory,
    )
    workspace_service = WorkspaceService(
        WorkspaceManager(
            default_path=settings.project_root,
            store=RecentWorkspaceStore(settings.workspace_state_path),
        )
    )

    return AppContainer(
        settings=settings,
        runtime=runtime,
        ollama_client=ollama_client,
        session_service=session_service,
        chat_service=chat_service,
        workspace_service=workspace_service,
        runtime_factory=runtime_factory,
    )
