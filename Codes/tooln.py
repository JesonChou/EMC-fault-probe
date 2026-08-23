from __future__ import annotations

import json
from collections.abc import Callable
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any

import chromadb
import numpy as np
import ollama

APP_DIR = Path(__file__).resolve().parent
VECTOR_DB_PATH = APP_DIR / "emc_vector_db"
COLLECTION_NAME = "emc_faults"
EMBED_MODEL = "nomic-embed-text"
DEFAULT_TOP_K = 5


# name -> 工具描述、参数 Schema、Python 函数
TOOLS: dict[str, dict[str, Any]] = {}


def tool(
    name: str,
    description: str,
    parameters: dict[str, Any],
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    工具注册装饰器。

    装饰器本身不调用工具，只负责将工具元信息和函数对象
    保存到 TOOLS 注册表中。
    """
    def decorator(function: Callable[..., Any]) -> Callable[..., Any]:
        TOOLS[name] = {
            'name': name,
            'description': description,
            'parameters': parameters,
            'func': function,
        }
        return function

    return decorator

def native_tools() -> list[dict[str, Any]]:
    """
    将内部工具注册表转化为 Ollama 原生 tools 的格式

    """
    return [
        {
            'type': 'function',
            'function':{
                'name': entry['name'],
                'description': entry['description'],
                # 防止 SDK 或者后续代码修改原始 Schema
                'parameters': deepcopy(entry['parameters']),
            }
        }
        for entry in TOOLS.values()
    ]


def embed_text(text: str) -> list[float]:
    """ 使用 Ollama embedding 模型生成文本向量 """
    response = ollama.embed(
        model = EMBED_MODEL,
        input = text,
    )
    return response['embeddings'][0]

def cosine_similarity(
        query_vector: np.ndarray,
        file_vector: np.ndarray
) -> np.ndarray:
    """ 计算 query 向量与所有故障条目的余弦相似度。 """
    return (file_vector / np.linalg.norm(file_vector, axis=1, keepdims=True)) @ (query_vector / np.linalg.norm(query_vector))


@lru_cache(maxsize = 1)
def get_collection():
    """
    惰性连接 ChromaDB。

    lru_cache(maxsize = 1) 保证当前进程只建立一次连接。
    """
    client = chromadb.PersistentClient(
        path=str(VECTOR_DB_PATH),
    )

    try:
        return client.get_collection(
            name = COLLECTION_NAME,
        )
    except Exception:  # noqa: BLE001
        raise RuntimeError(
            f"找不到向量库：{VECTOR_DB_PATH}，"
            f"集合名称：{COLLECTION_NAME}。"
            "请先运行 Embedding_Test.py 建立向量库。"
        ) from None


SEARCH_CASES_PARAMETERS = {
    'type': 'object',
    'required': ['query', 'top_k'],
    'properties': {
        'query': {
            'type': 'string',
            'description': (
                '用户的电磁兼容故障描述或检索关键词，'
                '例如：辐射发射超标'
            ),
        },
        'top_k': {
            'type': 'integer',
            'description': '返回最相关的故障条目数量',
            'minimum': 1,
            'maximum': 10,
        },
    },

}

@tool(
    "search_cases",
    "在电磁兼容故障库中检索故障词条。当用户描述故障现象、询问故障原因或解决方案时调用。"
    "返回匹配词条，每条含故障对象/故障现象/故障原因/解决方案/故障等级/发生频率。",
    parameters = SEARCH_CASES_PARAMETERS,
)
def search_cases(query: str, top_k: int = DEFAULT_TOP_K) -> str:
    """
    向量化 query -> 余弦相似度排序 -> 返回 Top-K 词条文本

    返回值是给模型的紧凑文本而不是给用户看到的UI排版
    """
    collection = get_collection()
    data  = collection.get(include=["embeddings","metadatas"])

    file_vectors = np.array(data["embeddings"]) # (N, 768)
    metas = data["metadatas"]                   # N 条原始 JSON

    q_vec = np.array(embed_text(query))
    scores = cosine_similarity(q_vec, file_vectors)
    top_idx = np.argsort(scores)[::-1][:top_k]

    lines = []
    for i in top_idx:
        m = metas[i]
        lines.append(
            f"[词条{i}] 相似度{scores[i]:.4f}\n"
            f"故障对象：{m['故障对象']}\n"
            f"故障现象：{m['故障现象']}\n"
            f"故障原因：{m['故障原因']}\n"
            f"解决方案：{m['解决方案']}\n"
            f"故障等级：{m['故障等级']}\n"
            f"发生频率：{m['发生频率']}"
        )
    return "\n\n".join(lines)

if __name__ == "__main__":
    print("已注册工具：")
    print(list(TOOLS.keys()))

    print("\nOllama 原生 tools Schema：")
    print(
        json.dumps(
            native_tools(),
            ensure_ascii=False,
            indent=2,
        )
    )


    def handle_callable(obj):
        if callable(obj):
            # 返回函数名（如果存在），否则返回通用标识
            return f"<function {obj.__name__ if hasattr(obj, '__name__') else 'anonymous'}>"
        # 其他不可序列化类型可继续扩展
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    print("\nTOOLS JSON 结构：")
    print(json.dumps(TOOLS, ensure_ascii=False, default=handle_callable, indent=2))


    print("\n直接调用 search_cases：")
    print(
        search_cases(
            query = "设备辐射发射超标怎么办？",
            top_k = 3,
        )
    )
