import json  # 用于生成JSONL 每行消息的序列化/反序列化
import secrets  # 生成会话 id 的随机后端
import subprocess
import time
import urllib.request  # 用于探测 Ollama HTTP 服务是否已就绪
from datetime import datetime  # 用于消息时间戳
from pathlib import Path  # 会话文件的路径操作

import chromadb
import numpy as np
import ollama
from ollama import ChatResponse, chat

data_path = "./emc_vector_db"
collection_name = "emc_faults"

model_name = 'deepseek-r1:7b'

system = "你是一个电磁兼容领域的专家，负责以严谨专业的态度给用户提出的电磁兼容故障问题进行解答。请结合用户问题和资料进行回答。"

item_num = 5 # 最匹配词条数目

USER_PROMPT_TEMPLATE = (
    "以下是从电磁兼容故障库中检索到的相关资料：\n\n"
    "{context}\n\n用户问题：{question}\n\n请结合上述资料回答。"
)

# ═══════════════════════════════════════════════════════════
#   之前：
#   多轮对话的"记忆"：全局列表 history
#   每个元素是一个元组 (用户问题, 模型回答)
#   元组 (a, b) = 把两个值绑成一对；列表 = 按顺序排的一串
#   第 1 轮结束后 → [(q1, a1)]
#   第 2 轮结束后 → [(q1, a1), (q2, a2)]
#   当前：
#   history变量从上述的(问题，回答)元组变更为消息字典（与磁盘 JSONL 同构）：
#     user 词条      → {"role": "user", "content": 纯问题, "context": 该轮RAG资料}
#     assistant 词条 → {"role": "assistant", "content": 正式回答}
# ═══════════════════════════════════════════════════════════

history = [] # 多轮对话记忆变量

# 会话文件存放目录
SESSIONS_DIR = Path(__file__).resolve().parent / "chat_sessions"

# 向量化字符文本
def embed_text(text:str) -> list[float]:
    resp =ollama.embed(model = "nomic-embed-text", input = text)
    return resp["embeddings"][0]

# 计算余弦相似度
# a 表示词条向量化得到的矩阵，b 表示query向量化得到的单一向量
# @ 为矩阵乘法运算

def cosine_similarity(b: np.ndarray, a: np.ndarray) -> np.ndarray:
    return (a/ np.linalg.norm(a, axis=1,keepdims=True)) @ (b / np.linalg.norm(b))

# ═══ Ollama 服务管理 ═══
# 背景：Windows 版 Ollama 通常已注册为系统服务自动常驻，无需手动启动。
# 注意：`ollama run` 是交互式对话 REPL（会阻塞占用模型），不是服务启动方式；
# 正确常驻服务命令是 `ollama serve`（监听 127.0.0.1:11434，供 SDK 调用）。
# 因此启动前先探测服务是否已在运行，避免重复启动；未运行才用 serve 拉起。

def is_ollama_serving() -> bool:
    """
    探测 Ollama HTTP 服务是否已在运行。

    通过请求 Ollama 默认端口（11434）的 /api/tags 接口判断：
    能连通 → 服务可用，直接调用即可；连不通 → 需要手动启动。
    """
    try:
        urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=2)
        return True
    except OSError:  # 连接失败/超时均属 OSError 家族（URLError 为其子类）
        return False


def start_ollama_background():
    """确保 Ollama serve 在后台运行。

    返回：
        None    → 服务本来就在运行（系统服务/之前已启动），无需管理；
        process → 本次由本函数启动的 serve 进程句柄，用完应 terminate()。
    """
    # ① 已在运行（Windows 安装版通常注册为系统服务自动常驻）→ 直接用
    if is_ollama_serving():
        print("Ollama 服务已在运行")
        return None

    # ② 用 `ollama serve` 后台启动常驻服务（不是交互式的 `ollama run`）
    #    日志重定向到文件：若用 PIPE 且不读取，管道写满会阻塞进程。
    #    用 with 管理文件：Popen 返回后子进程已持有句柄副本，父进程关闭不影响写日志。
    with open("ollama_serve.log", "a", encoding="utf-8") as log:
        process = subprocess.Popen(
            ["ollama", "serve"],
            stdout=log,
            stderr=subprocess.STDOUT,
        )
    print(f"Ollama serve 已启动，进程ID: {process.pid}（日志见 ollama_serve.log）")

    # ③ 轮询等待服务就绪（服务冷启动需要几秒，最多等 15 秒）
    for _ in range(30):
        if is_ollama_serving():
            print("Ollama 服务就绪")
            return process
        time.sleep(0.5)

    print("警告：Ollama 服务 15 秒内未就绪，请检查 ollama_serve.log")
    return process


# 拼接消息列表
def build_messages(question: str, context: str) -> list:
    # 按照DeepSeek官方缓存命中规则拼接消息列表

    # 1、人设，前缀第一段，永远不变
    messages = [{"role": "system", "content": system}]

    # 2、把历史问答原样回放给模型
    # for question_prev, answer_prev in history:
    #     messages.append({"role": "user", "content": question_prev})
    #     messages.append({"role": "assistant", "content": answer_prev})
    for msg in history:
        if msg["role"] == "user":
            messages.append({
                "role": "user", 
                "content": USER_PROMPT_TEMPLATE.format(
                    context = msg.get("context", ""), 
                    question = msg["content"],
                ),
            })
        elif msg["role"] == "assistant":
            messages.append({"role": "assistant", "content": msg["content"]})

    # 3、将本轮新内容拼接到最后
    messages.append({
        "role": "user",
        "content": USER_PROMPT_TEMPLATE.format(context=context, question=question)
    })
    return messages


# 读取对话消息
def resume_session(session_id: str) -> list[dict]:
    """
    读取会话全部消息（按时间顺序），返回填充给全局 history。

    遇到解析失败的行（上次运行崩溃留下的半行 JSON）直接跳过，不中断恢复。
    """
    messages = []
    with open(SESSIONS_DIR / f"{session_id}.jsonl", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue # 崩溃残留，丢弃
            if obj.get("type") == "message":
                messages.append(obj)
    return messages


def now_ts() -> str:
    """当前时间字符串（ISO 格式，秒级），作为消息行的时间戳。"""
    return datetime.now().isoformat(timespec="seconds")


def new_session() -> str:
    """新建会话文件（先写入首行会话头），返回 session_id。

    会话 id = 时间戳 + 4 位随机 hex：同一秒创建多个会话也不会撞名。
    """
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    session_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(2)
    header = {"type": "session", "session_id": session_id, "created_at": now_ts()}
    with open(SESSIONS_DIR / f"{session_id}.jsonl", "w", encoding="utf-8") as f:
        f.write(json.dumps(header, ensure_ascii=False) + "\n")
    return session_id


def append_message(session_id: str, role: str, content: str,
                   context: str | None = None, thinking: str | None = None,
                   hit_ids: list[int] | None = None) -> None:
    """向会话文件追加一行消息 JSON（只增不改）。

    role 为 user 时：记录 context（检索资料）与 hit_ids（命中词条编号）；
    role 为 assistant 时：记录 thinking（思考过程）。
    这些字段只落盘供展示/追溯，回放给模型时不用（见块 4 的 build_messages）。
    """
    message = {"type": "message", "role": role, "content": content, "ts": now_ts()}
    if role == "user":
        if context is not None:
            message["context"] = context
        if hit_ids is not None:
            message["hit_ids"] = hit_ids
    if role == "assistant" and thinking is not None:
        message["thinking"] = thinking
    with open(SESSIONS_DIR / f"{session_id}.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(message, ensure_ascii=False) + "\n")
        f.flush()  # 立即刷盘：对话完成即落盘，不依赖程序正常退出


def list_sessions() -> list[dict]:
    """列出全部历史会话（按创建时间倒序），供启动时选择恢复。

    每条含：session_id / created_at / title（首问前 20 字）/
    turns（轮数 = user 消息数）/ updated_at（文件最后修改时间）。
    """
    sessions = []
    for path in sorted(SESSIONS_DIR.glob("*.jsonl")):
        info = {"session_id": "", "created_at": "", "title": "", "turns": 0}
        with open(path, encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if obj.get("type") == "session":
                    info["session_id"] = obj.get("session_id", path.stem)
                    info["created_at"] = obj.get("created_at", "")
                elif obj.get("type") == "message" and obj.get("role") == "user":
                    if not info["title"]:
                        info["title"] = obj.get("content", "")[:20]
                    info["turns"] += 1
        if info["session_id"]:
            info["title"] = info["title"] or "(空会话)"
            info["updated_at"] = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            sessions.append(info)
    sessions.sort(key=lambda s: s["created_at"], reverse=True)
    return sessions


ollama_process = start_ollama_background()

client = chromadb.PersistentClient(path = data_path)

collection = client.get_collection(name = collection_name)

data = collection.get(include=["embeddings", "metadatas"])

file_vectors = np.array(data["embeddings"])

metas = np.array(data["metadatas"])

### 启动时选择会话（恢复历史或者新建）
sessions = list_sessions()
if sessions:
    print("═══ 历史会话（磁盘已持久化，可随时恢复）═══")
    for i, s in enumerate(sessions, 1):
        print(f"[{i}] {s['created_at']} | {s['title']} | {s['turns']} 轮 | 更新于 {s['updated_at']}")
    choice = input("\n输入编号恢复会话，直接回车新建会话：").strip()
else:
    choice = ""
    print("暂无历史会话，将新建会话。")

if choice.isdigit() and 1 <= int(choice) <= len(sessions):
    session_id = sessions[int(choice) - 1]["session_id"]
    history = resume_session(session_id)  # 从磁盘恢复全部历史消息
    print(f"已恢复会话 {session_id}，共 {len(history)} 条消息，继续对话。\n")
else:
    session_id = new_session()
    history = []
    print(f"已新建会话 {session_id}。\n")

# 拼接结果预览（便于学习验证拼接效果）
# print("[system]\n" + system)
# print("\n[user]\n" + user_prompt)

# %%
try:
    while True:
        query = input("你(输入exit退出): ")
        if query.strip().lower() == "exit":
            break
        # print(query)

        # 对每轮用户的输入做向量化
        query_embedding = ollama.embed(model="nomic-embed-text", input=query)["embeddings"][0]

        # 做余弦相似度并取出最相似的几条
        scores = cosine_similarity(query_embedding, file_vectors)
        top_idx = np.argsort(scores)[::-1][:item_num]

        # 把检索到的资料格式化成结构化上下文
        context = "\n\n".join(
            f"[资料{i + 1}]\n"
            f"故障对象：{metas[idx]['故障对象']}\n"
            f"故障现象：{metas[idx]['故障现象']}\n"
            f"故障原因：{metas[idx]['故障原因']}\n"
            f"解决方案：{metas[idx]['解决方案']}\n"
            f"故障等级：{metas[idx]['故障等级']}\n"
            f"发生频率：{metas[idx]['发生频率']}"
            for i, idx in enumerate(top_idx)
        )

        # 用户问题先落盘，连同检索的资料和命中编号
        # 先落盘再生成，即使生成中途崩溃，问题也已经保存
        # np.int64 不能直接json序列化，要先转成int

        append_message(session_id, "user", query,
                       context=context, hit_ids=[int(i) for i in top_idx])

        messages = build_messages(query, context)

        response: ChatResponse = chat(
            model = model_name,
            messages = messages,
            # stream = False,
            stream = True,
            options={"num_ctx": 65535}, # 上下文窗口上限
        )
        # print(response['message']['content'])
        thinking_shown = False  # 标记：思考过程是否已经开始输出

        thinking_parts = []
        answer_parts = []
        for chunk in response:
            msg = chunk['message']
            # 思考过程：推理模型（如 deepseek-r1）的输出先进入 thinking 字段
            if msg.get('thinking'):
                if not thinking_shown:
                    print("[思考过程]")
                    thinking_shown = True
                print(msg['thinking'], end='', flush=True)
                thinking_parts.append(msg['thinking'])
                # 不应该在回放给模型的时候加上thinking的部分，除了会对模型思考质量产生影响外，token的开销也是比较大的。
                # 会话持久化时保存thinking并显示到UI，而回放给模型时只显示正式回答的部分
            # 正式回答：思考结束后，内容进入 content 字段
            if msg.get('content'):
                if thinking_shown:
                    print("\n───── 正式回答 ─────")
                    thinking_shown = False
                print(msg['content'], end='', flush=True)
                answer_parts.append(msg['content'])
        print()

        # 对于流式输出，response为生成器，只能用 for 循环取块
        answer = ''.join(answer_parts)
        thinking = ''.join(thinking_parts)

        # 下面三行是非流式输出的写法。对于非流式输出，response为完整字典，可以用下面的函数直接取
        # answer = response['message']['content']  # ← 单数 message，不是 messages
        # history.append((query, answer))
        # print(answer)

        # 正式回答落盘
        append_message(session_id, "assistant", answer, thinking = thinking or None)

        # history 更新
        # 在本测试脚本中，history由之前的元组变更为消息字典，与磁盘内容与格式保持一致
        history.append({"role": "user", "content": query, "context": context})
        history.append({"role": "assistant", "content": answer})

except Exception as e:  # noqa: BLE001 - 顶层兜底：任何生成异常都统一提示，便于定位
    print(f"生成失败: {e}")

finally:
    # 只有本次由 start_ollama_background() 启动的 serve 进程才需要关闭；
    # 服务原本就在运行（返回 None）时绝不能动它，否则会误杀系统服务
    if ollama_process is not None:
        ollama_process.terminate()
        print("已关闭本次启动的 Ollama serve 进程")
