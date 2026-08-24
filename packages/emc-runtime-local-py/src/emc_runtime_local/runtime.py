from __future__ import annotations

from collections.abc import AsyncIterator

from emc_core.agent.state import AgentState
from emc_core.domain.events import AgentEvent
from emc_core.ports.llm import LLM
from emc_core.tools.executor import ToolExecutor
from emc_core.tools.registry import ToolRegistry

from emc_runtime_local.loop import run_loop


class LocalRuntime:
    """
    基于项目自有 run_loop() 的本地 Agent Runtime。

    LocalRuntime 不创建 Ollama Client、不连接 ChromaDB，也不读取环境变量。
    这些具体依赖由后端或桌面应用的 composition.py 创建后传入。
    """

    def __init__(
        self,
        *,
        llm: LLM,
        registry: ToolRegistry,
        max_steps: int = 5,
    ) -> None:
        if max_steps < 1:
            raise ValueError("max_steps 必须大于 0")

        # 依赖注入：Runtime 保存接口对象，而不是在内部写死 Ollama 或工具。
        self._llm = llm
        self._registry = registry
        self._executor = ToolExecutor(registry)
        self._max_steps = max_steps

    async def run(
        self,
        *,
        state: AgentState,
    ) -> AsyncIterator[AgentEvent]:
        """把底层 run_loop() 的事件原样转发给应用层。"""

        # 这里需要 async for + yield，而不是简单 await run_loop()：
        # run_loop() 是异步生成器，返回的是事件流，不是单个最终值。
        async for event in run_loop(
            state=state,
            llm=self._llm,
            tools=self._registry.specs(),
            execute_tool=self._executor.execute,
            max_steps=self._max_steps,
        ):
            yield event
