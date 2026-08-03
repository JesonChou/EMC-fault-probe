import subprocess
import time
import urllib.request  # 用于探测 Ollama HTTP 服务是否已就绪

import chromadb
import numpy as np
import ollama
from ollama import ChatResponse, chat

data_path = "./emc_vector_db"
collection_name = "emc_faults"

model_name = 'deepseek-r1:7b'

system = "你是一个电磁兼容领域的专家，负责以严谨专业的态度给用户提出的电磁兼容故障问题进行解答。请结合用户问题和资料进行回答。"

item_num = 5 # 最匹配词条数目

# ═══════════════════════════════════════════════════════════
# 多轮对话的"记忆"：全局列表 history
#   每个元素是一个元组 (用户问题, 模型回答)
#   元组 (a, b) = 把两个值绑成一对；列表 = 按顺序排的一串
#   第 1 轮结束后 → [(q1, a1)]
#   第 2 轮结束后 → [(q1, a1), (q2, a2)]
# ═══════════════════════════════════════════════════════════

history = [] # 多轮对话记忆变量

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
    for question_prev, answer_prev in history:
        messages.append({"role": "user", "content": question_prev})
        messages.append({"role": "assistant", "content": answer_prev})

    # 3、将本轮新内容拼接到最后
    messages.append({
        "role": "user",
        "content": (
            f"以下是从电磁兼容故障库中检索到的相关资料：\n\n"
            f"{context}\n\n用户问题：{question}\n\n请结合上述资料回答。"
        ),
    })
    return messages


ollama_process = start_ollama_background()

client = chromadb.PersistentClient(path = data_path)

collection = client.get_collection(name = collection_name)

data = collection.get(include=["embeddings", "metadatas"])

file_vectors = np.array(data["embeddings"])

metas = np.array(data["metadatas"])

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

        answer_parts = []
        for chunk in response:
            msg = chunk['message']
            # 思考过程：推理模型（如 deepseek-r1）的输出先进入 thinking 字段
            if msg.get('thinking'):
                if not thinking_shown:
                    print("[思考过程]")
                    thinking_shown = True
                print(msg['thinking'], end='', flush=True)
                # answer_parts.append(msg['thinking'])
                # 不应该在回放给模型的时候加上thinking的部分，除了会对模型思考质量产生影响外，token的开销也是比较大的。
                # 对于后续的持久化方案，建议会话持久化时保存thinking并显示到UI，而回放给模型时只显示正式回答的部分
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
        history.append((query, answer))

        # 下面三行是非流式输出的写法。对于非流式输出，response为完整字典，可以用下面的函数直接取
        # answer = response['message']['content']  # ← 单数 message，不是 messages
        # history.append((query, answer))
        # print(answer)

except Exception as e:  # noqa: BLE001 - 顶层兜底：任何生成异常都统一提示，便于定位
    print(f"生成失败: {e}")

finally:
    # 只有本次由 start_ollama_background() 启动的 serve 进程才需要关闭；
    # 服务原本就在运行（返回 None）时绝不能动它，否则会误杀系统服务
    if ollama_process is not None:
        ollama_process.terminate()
        print("已关闭本次启动的 Ollama serve 进程")
