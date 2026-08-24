from __future__ import annotations

import inspect
from collections.abc import Callable, Mapping
from typing import Any, get_type_hints

from emc_core.tools.models import ToolCall, ToolResult
from emc_core.tools.registry import ToolRegistry


def _get_type_hints(handler: Callable[..., Any]) -> dict[str, Any]:
    """读取普通函数或可调用对象（实现了 __call__）的参数类型。"""

    # 对普通函数，直接读取 handler；对 SearchCasesTool 这类可调用对象，
    # 类型注解实际写在 __call__ 方法上，所以改为读取 handler.__call__。
    target = handler
    if not inspect.isfunction(handler) and not inspect.ismethod(handler):
        target = handler.__call__

    try:
        return get_type_hints(target)
    except (NameError, TypeError):
        # 类型注解只帮助参数转换；读取失败不应阻止工具执行。
        return {}


def _coerce_arguments(
    *,
    handler: Callable[..., Any],
    raw_arguments: Mapping[str, Any],
) -> dict[str, Any]:
    """根据 handler 的类型注解转换模型返回的参数。"""

    signature = inspect.signature(handler)
    type_hints = _get_type_hints(handler)
    arguments = dict(raw_arguments)

    for parameter_name, parameter in signature.parameters.items():
        if parameter_name not in arguments:
            continue

        value = arguments[parameter_name]
        expected_type = type_hints.get(
            parameter_name,
            parameter.annotation,
        )

        try:
            if expected_type is int:
                value = int(value)
            elif expected_type is float:
                value = float(value)
            elif expected_type is str:
                value = str(value)
        except (TypeError, ValueError):
            # 转换失败时保留原值，让真正的 handler 给出更具体的业务错误。
            pass

        arguments[parameter_name] = value

    return arguments


class ToolExecutor:
    """
    执行模型发出的统一 ToolCall。

    ToolExecutor 不认识 Ollama 的 ToolCall 类型，
    只认识项目内部定义的 emc_core.tools.models.ToolCall。

    这就是“适配器边界”：

    Ollama ToolCall
        ↓ 由 Ollama Adapter 转换
    项目统一 ToolCall
        ↓
    ToolExecutor
    """

    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    async def execute(self, tool_call: ToolCall) -> ToolResult:
        """
        查找并执行一个工具。

        这个方法使用 async def，是因为工具将来可能执行：

        - 数据库查询
        - HTTP 请求
        - 文件操作
        - 本地模型调用

        这些操作通常需要异步等待。
        """

        registered_tool = self._registry.get(tool_call.name)

        if registered_tool is None:
            return ToolResult(
                tool_name=tool_call.name,
                call_id=tool_call.call_id,
                error=f"未注册工具：{tool_call.name}",
            )

        try:
            arguments = _coerce_arguments(
                handler=registered_tool.handler,
                raw_arguments=tool_call.arguments,
            )

            # ** 是 Python 的字典解包语法。
            #
            # 如果 arguments 是：
            #
            # {
            #     "query": "辐射发射超标",
            #     "top_k": 3,
            # }
            #
            # 那么下面的调用等价于：
            #
            # handler(
            #     query="辐射发射超标",
            #     top_k=3,
            # )
            output: Any = registered_tool.handler(**arguments)

            # handler 既可能是普通函数，也可能是 async 函数。
            #
            # 普通函数会直接返回结果；
            # async 函数调用后会返回 awaitable 对象。
            #
            # inspect.isawaitable() 让执行器同时兼容这两类工具。
            if inspect.isawaitable(output):
                output = await output

            return ToolResult(
                tool_name=tool_call.name,
                call_id=tool_call.call_id,
                output=output,
            )

        except Exception as exc:  # noqa: BLE001
            # 工具可能来自数据库、第三方库或外部插件，
            # 因此这里需要捕获工具边界内的所有常规异常。
            #
            # 不继续 raise，是因为 Agent 需要把错误结果回填给模型，
            # 让模型解释错误或决定是否换一种方式继续。
            return ToolResult(
                tool_name=tool_call.name,
                call_id=tool_call.call_id,
                error=f"{type(exc).__name__}: {exc}",
            )
