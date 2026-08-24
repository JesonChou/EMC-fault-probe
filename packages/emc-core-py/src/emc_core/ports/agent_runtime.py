from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol

from emc_core.agent.state import AgentState
from emc_core.domain.events import AgentEvent


class AgentRuntime(Protocol):
    """
    后端和桌面应用共同依赖的 Agent Runtime 接口。

    应用层只知道 run() 会产生 AgentEvent，不需要知道底层使用 Ollama、
    云端 API、LangGraph 还是其他 Agent 框架。
    """

    def run(
        self,
        *,
        state: AgentState,
    ) -> AsyncIterator[AgentEvent]:
        """从给定状态开始运行，并以异步流形式返回事件。"""
        ...
