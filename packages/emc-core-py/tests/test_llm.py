import asyncio
from collections.abc import Sequence

from emc_core.ports.llm import LLM, ChatMessage, LLMOutput
from emc_core.tools.models import ToolCall, ToolSpec


class FakeLLM:
    """用于验证 LLM 接口的最小假模型。"""

    def __init__(self, output: LLMOutput) -> None:
        self.output = output
        self.received_messages: Sequence[ChatMessage] = ()
        self.received_tools: Sequence[ToolSpec] = ()

    async def complete(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[ToolSpec],
    ) -> LLMOutput:
        self.received_messages = messages
        self.received_tools = tools
        return self.output


def test_llm_can_return_final_text() -> None:
    llm: LLM = FakeLLM("这是最终回答。")

    output = asyncio.run(
        llm.complete(
            messages=[
                {
                    "role": "user",
                    "content": "请直接回答。",
                }
            ],
            tools=[],
        )
    )

    assert output == "这是最终回答。"


def test_llm_can_return_tool_call() -> None:
    expected = ToolCall(
        name="search_cases",
        arguments={
            "query": "辐射发射超标",
        },
        call_id="call-001",
    )

    llm: LLM = FakeLLM(expected)

    output = asyncio.run(
        llm.complete(
            messages=[
                {
                    "role": "user",
                    "content": "查询辐射发射超标案例。",
                }
            ],
            tools=[
                ToolSpec(
                    name="search_cases",
                    description="查询 EMC 故障案例。",
                    parameters={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                            },
                        },
                        "required": ["query"],
                    },
                )
            ],
        )
    )

    assert isinstance(output, ToolCall)
    assert output.name == "search_cases"
    assert output.arguments["query"] == "辐射发射超标"
    assert output.call_id == "call-001"


def test_fake_llm_receives_messages_and_tools() -> None:
    tool = ToolSpec(
        name="search_cases",
        description="查询 EMC 故障案例。",
    )
    llm = FakeLLM("完成")

    asyncio.run(
        llm.complete(
            messages=[
                {
                    "role": "user",
                    "content": "查询案例。",
                }
            ],
            tools=[tool],
        )
    )

    assert llm.received_messages[0]["role"] == "user"
    assert llm.received_tools[0].name == "search_cases"
