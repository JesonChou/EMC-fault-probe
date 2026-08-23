import subprocess
import time

from ollama import ChatResponse
from ollama import chat

model_name = 'deepseek-r1:8b'


def start_ollama_background():
    """在后台启动Ollama服务"""
    try:
        # 使用Popen在后台启动服务
        process = subprocess.Popen(
            ['ollama', 'run', model_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        print(f"Ollama服务已启动，进程ID: {process.pid}")

        # 让服务运行一段时间
        time.sleep(1)

        # 检查进程是否还在运行
        if process.poll() is None:
            print("Ollama服务正在运行中...")
        else:
            print("Ollama服务已停止")

        return process

    except Exception as e:
        print(f"启动失败: {e}")
        return None


# 启动服务
ollama_process = start_ollama_background()

# %%
try:
    contents = '请提取出“传导发射与辐射发射超标”的关键词，只输出关键词，不要有任何其他的输出'
    # 直接输出
    response: ChatResponse = chat(
        model=model_name,
        messages=[{'role': 'user', 'content': contents, }],
        stream=False,
    )
    print(response['message']['content'])
    # for chunk in response:
    #     print(chunk['message']['content'], end='', flush=True)

except Exception as e:
    print(f"生成失败: {e}")

# or access fields directly from the response object
# print(response.message.content)
