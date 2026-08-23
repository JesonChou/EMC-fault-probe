

"""
Embedding_Test.py — RAG 文本嵌入与向量检索原理测试脚本
========================================================

【文件用途】
本文件用于测试和验证 RAG（检索增强生成）流程中「向量化检索」这一环节的
原理与实现，不涉及 LLM 生成部分。运行后可观察到完整的两个阶段：
数据入库（文本 → 向量 → 存储）与相似度检索（问题 → 向量 → 余弦比对 → Top-K）。

【核心原理】
RAG 的第一步是把"语义"变成"数字"：
  1. 嵌入模型（embedding model）：将一段文本映射为 768 维浮点向量
     （本文件使用 Ollama 提供的 nomic-embed-text 模型）。
     语义相近的文本，其向量在空间中距离也近——这是检索能"懂语义"的根本原因。
  2. 向量数据库（ChromaDB）：负责向量的持久化存储与读取，
     存向量时同时挂载原始 JSON 元数据（metadatas），供检索命中后直接返回。
  3. 相似度检索：将用户 query 用【同一个】嵌入模型向量化后，
     与本文件自写的余弦相似度算法比对全库向量，取相似度最高的前 5 条。
     注意：本文件刻意不用 collection.query()（库内置 HNSW 索引检索），
     而是用 collection.get() 全量取出 + 自写余弦排序，目的是直观展示
     "向量相似度检索"的数学本质；二者结果等价。

【运行流程】
  阶段一  建库（脚本上半部分，for 循环）：
    data_1.json ──→ 每条记录 6 个字段拼接成一段文本
                 ──→ embed_text() 嵌入为 768 维向量
                 ──→ collection.add() 连同原始 JSON 一起写入 experiments/rag/emc_vector_db

  阶段二  检索（脚本下半部分）：
    固定 query ──→ embed_text() 嵌入
              ──→ cosine_similarity() 与全库向量逐一比对
              ──→ np.argsort 降序取前 5 条 ──→ 打印相似度与原始字段

【运行前置条件】
  - 本机已启动 Ollama 服务，并已拉取嵌入模型：
        ollama pull nomic-embed-text
  - 已安装依赖：pip install chromadb ollama numpy
  - 从仓库任意目录运行（脚本按自身目录定位 experiments/rag/emc_vector_db，数据定位到 data/published/v1/data_1.json）

【注意事项】
  - 建库只应执行一次：重复运行会因 id（"0"~"54"）已存在而报错。
    如需重建库，请先删除 experiments/rag/emc_vector_db 目录。
  - 建库与检索必须使用同一个嵌入模型，否则向量不在同一语义空间，
    余弦相似度将失去意义。
  - 从 ChromaDB 取回的 metadata 字段顺序与 JSON 文件不一致属正常现象
    （内部以 HashMap 存储，键顺序不保证），不影响按键访问。

【学习延伸】
  生产环境中数据量大时，应改用 collection.query() 利用 HNSW 索引加速检索，
  并可通过 where 参数按 metadata 字段过滤；本文件的自写余弦算法在数据量
  小时结果与其完全一致，便于理解检索原理。
"""

import json, chromadb, ollama
from pathlib import Path
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
VECTOR_DB_PATH = Path(__file__).resolve().parent / "emc_vector_db"
DATA_FILE = PROJECT_ROOT / "data" / "published" / "v1" / "data_1.json"

# 向量化字符文本
def embed_text(text:str) -> list[float]:
    resp =ollama.embed(model = "nomic-embed-text", input = text)
    return resp["embeddings"][0]

# 余弦相似度
# a 表示词条向量化得到的矩阵，b 表示query向量化得到的单一向量
# @ 为矩阵乘法运算
def cosine_similarity(b: np.ndarray, a: np.ndarray) -> np.ndarray:
    return (a/ np.linalg.norm(a, axis=1,keepdims=True)) @ (b / np.linalg.norm(b))

# ═══ 建库（只做一次）═══

# PersistentClint函数，指持久化到客户端，数据会真实写到磁盘，程序关闭或者电脑重启，数据还在
# 输入参数为数据写入路径

client = chromadb.PersistentClient(path=str(VECTOR_DB_PATH))

# collection 指数据库中的一张表，各存各的向量

collection = client.get_or_create_collection(name="emc_faults")

# 从json文件中提取出来的原始词条

entries = json.load(DATA_FILE.open(encoding="utf-8"))

for i, item in enumerate(entries):
    text = (
        f"故障对象：{item['故障对象']}。"
        f"故障现象：{item['故障现象']}。"
        f"故障原因：{item['故障原因']}。"
        f"解决方案：{item['解决方案']}。"
        f"故障等级：{item['故障等级']}。"
        f"发生频率：{item['发生频率']}。"
    )
    collection.add(
        ids = str(i), # 该条记录的编号
        embeddings = embed_text(text), # 每一个记录的向量化数据
        metadatas = [item], # 原始json数据
    )

query = "请你告诉我当设备出现辐射发射超标的时候需要如何处置"

query_embedding = ollama.embed(model="nomic-embed-text", input=query)["embeddings"][0]

# query的向量化和数据的向量化做余弦

data  = collection.get(include=["embeddings", "metadatas"])

file_vectors = np.array(data["embeddings"])

metas = np.array(data["metadatas"])

scores = cosine_similarity(query_embedding, file_vectors)
top_idx = np.argsort(scores)[::-1][:5]
for i in top_idx:
    print(f"相似度 {scores[i]:.4f} | "
          f"{metas[i]['故障对象']} | {metas[i]['故障现象']} | {metas[i]['故障原因']} |"
          f"{metas[i]['解决方案']} | {metas[i]['故障等级']} | {metas[i]['发生频率']}")
