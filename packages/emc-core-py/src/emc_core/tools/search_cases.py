from __future__ import annotations

from emc_core.ports.retriever import RetrievalResult, Retriever
from emc_core.tools.models import ToolSpec

DEFAULT_TOP_K = 5

SEARCH_CASES_SPEC = ToolSpec(
    name="search_cases",
    description=(
        "在电磁兼容故障库中检索故障词条。"
        "当用户描述故障现象、询问故障原因或解决方案时调用。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "用户的电磁兼容故障描述或检索关键词，例如：辐射发射超标"
                ),
            },
            "top_k": {
                "type": "integer",
                "description": "返回最相关的故障词条数量。",
                "minimum": 1,
                "maximum": 10,
                "default": DEFAULT_TOP_K,
            },
        },
        # top_k 在 Python handler 中已有默认值，所以 JSON Schema 只要求 query。
        "required": ["query"],
        "additionalProperties": False,
    },
)


def _field(result: RetrievalResult, name: str) -> str:
    """安全读取 metadata 字段，并统一转换成字符串。"""

    value = result.metadata.get(name, "未知")
    return str(value)


def format_search_results(
    results: list[RetrievalResult],
) -> str:
    """把结构化检索结果转换成适合回填给 LLM 的紧凑文本。"""

    if not results:
        return "故障库中没有找到相关词条。"

    blocks: list[str] = []

    # enumerate(..., start=1) 同时得到从 1 开始的序号和当前结果。
    for index, result in enumerate(results, start=1):
        blocks.append(
            f"[词条 {index}] 余弦相似度：{result.score:.4f}\n"
            f"故障对象：{_field(result, '故障对象')}\n"
            f"故障现象：{_field(result, '故障现象')}\n"
            f"故障原因：{_field(result, '故障原因')}\n"
            f"解决方案：{_field(result, '解决方案')}\n"
            f"故障等级：{_field(result, '故障等级')}\n"
            f"发生频率：{_field(result, '发生频率')}"
        )

    return "\n\n".join(blocks)


class SearchCasesTool:
    """search_cases 的业务实现，通过 Retriever 注入具体检索技术。"""

    def __init__(self, retriever: Retriever) -> None:
        self._retriever = retriever

    async def __call__(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
    ) -> str:
        """
        执行故障案例检索。

        __call__ 让类的实例可以像函数一样调用。这样实例既能保存
        retriever 依赖，又能直接作为 ToolRegistry 的 handler。
        """

        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("query 不能为空")

        if not 1 <= top_k <= 10:
            raise ValueError("top_k 必须在 1 到 10 之间")

        results = await self._retriever.retrieve(
            query=normalized_query,
            limit=top_k,
        )
        return format_search_results(list(results))
