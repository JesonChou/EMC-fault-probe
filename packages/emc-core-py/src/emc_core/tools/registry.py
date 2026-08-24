from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from emc_core.tools.models import ToolSpec

# Callable[..., Any] 表示：
# 这是一个可以接收任意参数、返回任意结果的 Python 函数。
#
# 例如下面两种函数都可以作为 ToolHandler：
#
# def search_cases(query: str) -> str: ...
# async def search_cases(query: str) -> str: ...
ToolHandler = Callable[..., Any]


@dataclass(frozen=True, slots=True)
class RegisteredTool:
    """
    Runtime 内部保存的完整工具。

    spec:
        提供给 LLM 看的工具名称、说明和 JSON Schema。

    handler:
        真正执行工作的 Python 函数。

    ToolSpec 和 handler 分开保存非常重要：
    LLM 只能看到 spec，不能直接接触 Python 函数。
    """

    spec: ToolSpec
    handler: ToolHandler


class ToolRegistry:
    """
    工具注册表。

    它只负责两件事：

    1. 保存工具
    2. 根据工具名称查找工具

    它不负责执行工具，也不依赖 Ollama。
    因此以后更换模型时，这个类不需要改变。
    """

    def __init__(self) -> None:
        # 下划线开头表示这是类的内部属性，
        # 外部代码不应该直接修改
        self._tools: dict[str, RegisteredTool] = {}

    def register(
        self,
        *,
        spec: ToolSpec,
        handler: ToolHandler,
    ) -> None:
        """
        注册一个工具。

        参数前面的 * 表示后续参数必须使用关键字传递：

        registry.register(
            spec=tool_spec,
            handler=search_cases,
        )

        这样比 registry.register(tool_spec, search_cases) 更容易阅读。
        """

        if spec.name in self._tools:
            raise ValueError(f"工具已经注册：{spec.name}")

        self._tools[spec.name] = RegisteredTool(
            spec=spec,
            handler=handler,
        )

    def get(self, name: str) -> RegisteredTool | None:
        """
        根据名称查找工具。

        RegisteredTool | None 是联合类型，表示：

        - 找到时返回 RegisteredTool
        - 找不到时返回 None
        """

        return self._tools.get(name)

    def specs(self) -> list[ToolSpec]:
        """
        返回所有可以提供给 LLM 的工具描述。

        列表推导式的完整写法相当于：

        result = []
        for registered_tool in self._tools.values():
            result.append(registered_tool.spec)
        return result
        """

        return [registered_tool.spec for registered_tool in self._tools.values()]
