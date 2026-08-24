from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from functools import cached_property
from pathlib import Path

import chromadb
import numpy as np
from chromadb.errors import NotFoundError
from emc_core.ports.retriever import RetrievalResult, TextEmbedder


class ChromaCaseStore:
    """
    读取实验阶段已经建立的 ChromaDB 故障案例集合。

    当前数据库创建时使用的是 Chroma 默认 L2 空间，而原实验使用余弦
    相似度手动排序。为了保持实验结果不变，本类仍然全量读取向量并计算
    余弦相似度。后续重建 cosine HNSW 集合后，可改用 collection.query()。
    """

    def __init__(
        self,
        *,
        database_path: Path,
        collection_name: str,
    ) -> None:
        self._database_path = database_path.resolve()
        self._collection_name = collection_name

    @cached_property
    def client(self) -> chromadb.ClientAPI:
        """惰性创建并持有 Chroma Client。"""

        if not self._database_path.exists():
            raise FileNotFoundError(f"找不到 ChromaDB 目录：{self._database_path}")

        return chromadb.PersistentClient(
            path=str(self._database_path),
        )

    @cached_property
    def collection(self) -> chromadb.Collection:
        """
        第一次使用时连接 Chroma，之后复用同一个 Collection。

        cached_property 与普通 @property 的区别是：第一次计算后的返回值会
        缓存在实例中，后续访问不会重复创建 PersistentClient。
        """

        try:
            return self.client.get_collection(self._collection_name)
        except NotFoundError as exc:
            raise RuntimeError(
                f"找不到 Chroma collection：{self._collection_name}"
            ) from exc

    def search_by_cosine(
        self,
        *,
        query_embedding: Sequence[float],
        limit: int,
    ) -> list[RetrievalResult]:
        """用余弦相似度搜索最相关的故障案例。"""

        if limit < 1:
            raise ValueError("limit 必须大于 0")

        data = self.collection.get(
            include=["embeddings", "metadatas"],
        )
        raw_embeddings = data.get("embeddings")
        raw_metadatas = data.get("metadatas")

        if raw_embeddings is None or len(raw_embeddings) == 0:
            raise RuntimeError("Chroma collection 中没有 embedding 数据。")
        if raw_metadatas is None:
            raise RuntimeError("Chroma collection 中没有 metadata 数据。")

        case_vectors = np.asarray(raw_embeddings, dtype=np.float32)
        query_vector = np.asarray(query_embedding, dtype=np.float32)

        if case_vectors.ndim != 2 or query_vector.ndim != 1:
            raise ValueError("向量维度格式不正确。")
        if case_vectors.shape[1] != query_vector.shape[0]:
            raise ValueError(
                "查询向量与故障库向量维度不一致："
                f"{query_vector.shape[0]} != {case_vectors.shape[1]}"
            )

        case_norms = np.linalg.norm(
            case_vectors,
            axis=1,
            keepdims=True,
        )
        query_norm = np.linalg.norm(query_vector)

        if query_norm == 0 or np.any(case_norms == 0):
            raise ValueError("不能使用全零向量计算余弦相似度。")

        # @ 是矩阵乘法运算符。左侧是 (N, D) 的故障向量矩阵，右侧是
        # (D,) 的查询向量，结果是 (N,)：每条故障案例对应一个相似度。
        scores = (case_vectors / case_norms) @ (query_vector / query_norm)
        top_indices = np.argsort(scores)[::-1][:limit]

        results: list[RetrievalResult] = []
        for index in top_indices:
            metadata = raw_metadatas[int(index)]
            if not isinstance(metadata, Mapping):
                raise TypeError("Chroma metadata 必须是 object。")

            results.append(
                RetrievalResult(
                    score=float(scores[index]),
                    metadata=dict(metadata),
                )
            )

        return results


class ChromaRetriever:
    """组合 TextEmbedder 和 ChromaCaseStore，实现统一 Retriever 端口。"""

    def __init__(
        self,
        *,
        embedder: TextEmbedder,
        store: ChromaCaseStore,
    ) -> None:
        self._embedder = embedder
        self._store = store

    async def retrieve(
        self,
        query: str,
        limit: int,
    ) -> Sequence[RetrievalResult]:
        query_embedding = await self._embedder.embed(query)

        # Chroma 的 get() 是同步阻塞调用。asyncio.to_thread() 把它放到工作
        # 线程运行，避免阻塞负责 Ollama HTTP 请求的 asyncio 事件循环。
        return await asyncio.to_thread(
            self._store.search_by_cosine,
            query_embedding=query_embedding,
            limit=limit,
        )
