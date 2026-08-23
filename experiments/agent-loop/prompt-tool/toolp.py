import json
from functools import lru_cache
from pathlib import Path

import chromadb
import numpy as np
import ollama

### 全局常量

PROJECT_ROOT = Path(__file__).resolve().parents[3]
VECTOR_DB_PATH = PROJECT_ROOT / 'experiments' / 'rag' / 'emc_vector_db'
COLLECTION_NAME = "emc_faults"             # 向量集合名，和建库保持一致
EMBED_MODEL = "nomic-embed-text"           # 嵌入模型，和建库模型保持一致
DEFAULT_TOP_K = 5                          # 默认返回词条数

### 工具注册表 + 装饰器

TOOLS: dict[str, dict] = {} # 注册表: name -> {"name","description","parameters","func"}

def tool(name: str, description: str, parameters: dict):
    """
    装饰器，将函数注册进 TOOLS 注册表

    从tool这个函数来看，它的运行逻辑是这样的：
    Step 1: 参数 name、description、parameters 传入 tool 函数，然后 tool 函数开始执行；
    Step 2: 装饰器的语法是
        @tool(
            "search_cases",
            discription,
            parameters,
        )
        def func(...)
            ...

        这段语法等价于:
        def func(...)
            ...

        func = tool(...)(func)


        tool 的外层函数先执行，返回 decorator 函数
        此时 name/description/parameters 已经被闭包捕获
        然后， tool(...) 返回的 decorator 函数再执行，将函数 func 进行注册
        最后返回原函数 func
    """
    def decorator(func):
        TOOLS[name] = {
            "name": name,
            "description": description,
            "parameters": parameters, # JSON Schema
            "func": func,             # 真正的函数引用
        }
        return func
    return decorator


def tool_schemas_text() -> str:
    """
    将注册表序列化为"给模型看的说明书"(JSON 文本)
    只保留 name/descripton/parameters, 去掉 func
    func 是 Python 函数对象，无法序列化，也不该给模型看
    """
    schemas = [
        {k: v for k, v in entry.items() if k != "func"}
        for entry in TOOLS.values()
    ]
    return json.dumps(schemas, ensure_ascii=False, indent=2)


### 向量化 + 余弦相似度

def embed_text(text: str) -> list[float]:
    """ 将文本变为 768 维向量，采用nomic-embed-text嵌入模型"""
    resp = ollama.embed(model=EMBED_MODEL, input=text)
    return resp["embeddings"][0]


def cosine_similarity(b: np.ndarray, a: np.ndarray) -> np.ndarray:
    """余弦相似度：a 为全库向量矩阵（N, 768），b 为 query 向量（768,）。
    返回长度 N 的相似度数组。"""
    return (a / np.linalg.norm(a, axis=1, keepdims=True)) @ (b / np.linalg.norm(b))


### 向量库惰性连接(只初始化一次，避免每次检索重复建立连接)

@lru_cache(maxsize=1)
def get_collection():
    """惰性获取向量集合。lru_cache 保证整个进程只连接一次。

    PersistentClient 每次 new 都有磁盘 IO 和初始化开销；
    连接建立后 collection 可以重复查询。
    """
    client = chromadb.PersistentClient(path=str(VECTOR_DB_PATH))
    try:
        return client.get_collection(name=COLLECTION_NAME)
    except Exception:  # noqa: BLE001 - ChromaDB exceptions vary by backend/version
        raise RuntimeError(
            f"找不到向量库 {VECTOR_DB_PATH}（集合 {COLLECTION_NAME}）。"
            "请先运行 experiments/rag/embedding_test.py 完成建库。"
        ) from None


### 工具实现: search_cases(将RAG检索封装成工具)

"""
Schema 的 properties 字段是给模型说明要传入什么样的参数以及参数的含义
包含两个参数，一个是用户在输入框中输入的问题，也就是 query
还有一个是返回的最相关的词条数目 top_k。
top_k不是必须的，如果没有返回这个参数，则回退到默认条目
"""

SEARCH_CASES_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "用户的故障描述或检索关键词，如'辐射发射超标'",
        },
        "top_k": {
            "type": "integer",
            "description": "返回词条数量",
            "minimum": 1,
            "maximum": 10,
        },
    },
    "required": ["query"],
}


@tool(
    "search_cases",
    "在电磁兼容故障库中检索故障词条。当用户描述故障现象、询问故障原因或解决方案时调用。"
    "返回匹配词条，每条含故障对象/故障现象/故障原因/解决方案/故障等级/发生频率。",
    SEARCH_CASES_SCHEMA,
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


#   独立自测入口（第一步测试：先验证工具本身）

if __name__ == "__main__":
    print("已注册工具：", list(TOOLS.keys()))
    print("\n给模型看的工具说明书：")
    print(tool_schemas_text())
    print("\n直接调用 search_cases 测试（不经过 LLM）：")
    print(search_cases("辐射发射超标怎么办", top_k=3))
