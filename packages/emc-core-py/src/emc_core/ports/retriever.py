from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    """一次检索命中的统一结果，不暴露 Chroma 等具体数据库类型。"""

    score: float
    metadata: Mapping[str, Any]


class TextEmbedder(Protocol):
    """文本嵌入端口；Ollama 和未来的云端嵌入服务都可以实现它。"""

    async def embed(self, text: str) -> Sequence[float]:
        """把文本转换成浮点向量。"""
        ...


class Retriever(Protocol):
    """向量检索端口；业务工具只依赖这个接口。"""

    async def retrieve(
        self,
        query: str,
        limit: int,
    ) -> Sequence[RetrievalResult]:
        """返回与 query 最相关的结果，按 score 从高到低排序。"""
        ...
