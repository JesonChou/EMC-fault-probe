from __future__ import annotations

import asyncio
from collections.abc import Sequence

from emc_core.ports.retriever import RetrievalResult
from emc_core.tools.search_cases import SearchCasesTool


class FakeRetriever:
    """离线测试替身：无需 Ollama 和 ChromaDB。"""

    def __init__(self) -> None:
        self.calls: list[tuple[str, int]] = []

    async def retrieve(
        self,
        query: str,
        limit: int,
    ) -> Sequence[RetrievalResult]:
        self.calls.append((query, limit))
        return [
            RetrievalResult(
                score=0.91234,
                metadata={
                    "故障对象": "测试设备",
                    "故障现象": "辐射发射超标",
                    "故障原因": "屏蔽不连续",
                    "解决方案": "改善屏蔽搭接",
                    "故障等级": "严重",
                    "发生频率": "偶发",
                },
            )
        ]


def test_search_cases_uses_retriever_and_formats_result() -> None:
    retriever = FakeRetriever()
    tool = SearchCasesTool(retriever)

    output = asyncio.run(
        tool(
            query="  辐射发射超标  ",
            top_k=3,
        )
    )

    assert retriever.calls == [("辐射发射超标", 3)]
    assert "余弦相似度：0.9123" in output
    assert "故障对象：测试设备" in output
    assert "解决方案：改善屏蔽搭接" in output
