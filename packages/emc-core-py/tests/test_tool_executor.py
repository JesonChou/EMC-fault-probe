from __future__ import annotations

import asyncio

import pytest
from emc_core.tools.executor import ToolExecutor
from emc_core.tools.models import ToolCall, ToolSpec
from emc_core.tools.registry import ToolRegistry

SPEC = ToolSpec(
    name="echo",
    description="返回输入文本。",
    parameters={
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    },
)


def test_registry_exposes_specs_and_rejects_duplicate_names() -> None:
    registry = ToolRegistry()
    registry.register(spec=SPEC, handler=lambda text: text)

    assert registry.specs() == [SPEC]

    with pytest.raises(ValueError, match="工具已经注册"):
        registry.register(spec=SPEC, handler=lambda text: text)


def test_executor_supports_sync_and_async_handlers() -> None:
    sync_registry = ToolRegistry()
    sync_registry.register(spec=SPEC, handler=lambda text: text.upper())

    async def async_echo(text: str) -> str:
        return f"async:{text}"

    async_spec = ToolSpec(name="async_echo", description="异步回显")
    async_registry = ToolRegistry()
    async_registry.register(spec=async_spec, handler=async_echo)

    sync_result = asyncio.run(
        ToolExecutor(sync_registry).execute(
            ToolCall(name="echo", arguments={"text": "emc"})
        )
    )
    async_result = asyncio.run(
        ToolExecutor(async_registry).execute(
            ToolCall(name="async_echo", arguments={"text": "emc"})
        )
    )

    assert sync_result.output == "EMC"
    assert async_result.output == "async:emc"


def test_executor_converts_unknown_tool_and_exception_to_results() -> None:
    registry = ToolRegistry()

    def broken_tool() -> None:
        raise RuntimeError("boom")

    registry.register(
        spec=ToolSpec(name="broken", description="总是失败"),
        handler=broken_tool,
    )
    executor = ToolExecutor(registry)

    unknown_result = asyncio.run(executor.execute(ToolCall(name="missing")))
    broken_result = asyncio.run(executor.execute(ToolCall(name="broken")))

    assert unknown_result.error == "未注册工具：missing"
    assert broken_result.error == "RuntimeError: boom"


def test_executor_coerces_model_arguments_from_type_hints() -> None:
    registry = ToolRegistry()

    def repeat(text: str, count: int) -> str:
        return text * count

    registry.register(
        spec=ToolSpec(name="repeat", description="重复文本"),
        handler=repeat,
    )

    result = asyncio.run(
        ToolExecutor(registry).execute(
            ToolCall(
                name="repeat",
                arguments={
                    "text": 7,
                    "count": "3",
                },
            )
        )
    )

    assert result.output == "777"
