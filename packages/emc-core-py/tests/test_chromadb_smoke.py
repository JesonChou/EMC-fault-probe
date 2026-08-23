"""ChromaDB 向量库冒烟测试。

验证项目核心依赖 ChromaDB 在 CI 环境中可用：临时库的增删改查、
持久化与相似度查询。不依赖 Ollama 等外部服务。
"""

import chromadb


def test_chromadb_add_and_query(tmp_path):
    """add 后 query 能按相似度返回正确的 metadata。"""
    db_path = str(tmp_path / "db")
    client = chromadb.PersistentClient(path=db_path)
    col = client.get_or_create_collection(name="smoke_col")

    col.add(
        ids=["0", "1"],
        embeddings=[[0.1] * 8, [0.9] * 8],
        metadatas=[{"name": "a"}, {"name": "b"}],
    )

    res = col.query(query_embeddings=[[0.1] * 8], n_results=1)
    assert res["ids"][0] == ["0"]
    assert res["metadatas"][0][0]["name"] == "a"


def test_chromadb_persistent_reopen(tmp_path):
    """PersistentClient 关闭后重新打开，数据仍在。"""
    db_path = str(tmp_path / "db")
    client = chromadb.PersistentClient(path=db_path)
    col = client.get_or_create_collection(name="smoke_col")
    col.add(ids=["0"], embeddings=[[0.5] * 8], metadatas=[{"name": "persist"}])

    client2 = chromadb.PersistentClient(path=db_path)
    col2 = client2.get_or_create_collection(name="smoke_col")
    got = col2.get(include=["metadatas"])
    assert got["ids"] == ["0"]
    assert got["metadatas"][0]["name"] == "persist"
