from __future__ import annotations

import inspect
import json
import subprocess
import time
import urllib.request
from collections.abc import Mapping
from pathlib import Path
from typing import Any, get_type_hints

import ollama
from ollama import ChatResponse
from tooln import TOOLS, native_tools

APP_DIR = Path(__file__).resolve().parent

MODEL = "qwen3.5:9b-q4_K_M"
MAX_ITER = 5
THINK = True

# 为了方便 Prompt 与 Native 进行基准对照，
# 两个测试文件应使用同样的 temperature 和 seed。
OLLAMA_OPTIONS = {
    "temperature": 0,
    "seed": 42,
}

NATIVE_TOOLS = native_tools()

SYSTEM_PROMPT = (
    "你是电磁兼容领域专家，负责回答电磁兼容故障问题。\n"
    "当用户的问题需要查询故障库时，使用 search_cases 工具。\n"
    "得到工具结果后，必须结合工具结果回答，不要伪造故障库内容。"
)


def is_ollama_serving() -> bool:
    """检查 Ollama HTTP 服务是否已经运行。"""
    try:
        with urllib.request.urlopen(
            "http://127.0.0.1:11434/api/tags",
            timeout=2,
        ) as response:
            return response.status == 200
    except OSError:
        return False


def start_ollama_background():
    """
    如果 Ollama 服务尚未运行，则在后台启动 ollama serve。

    返回值：
    - None：表示服务原本已经运行
    - Popen 对象：表示本函数启动了服务
    """
    if is_ollama_serving():
        print("Ollama 服务已经运行。")
        return None

    log_path = APP_DIR / "ollama_serve.log"

    with log_path.open(
        "a",
        encoding="utf-8",
    ) as log_file:
        process = subprocess.Popen(
            ["ollama", "serve"],
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )

    print(
        f"Ollama serve 已启动，进程 ID：{process.pid}"
    )

    for _ in range(30):
        if is_ollama_serving():
            print("Ollama 服务已经就绪。")
            return process

        time.sleep(0.5)

    print(
        "警告：等待 Ollama 服务超过 15 秒，"
        "请检查 ollama_serve.log。"
    )

    return process


def coerce_arguments(
    tool_name: str,
    raw_arguments: Mapping[str, Any],
) -> dict[str, Any]:
    """
    将 Native tool call 中的 arguments 转换为 Python 函数参数。

    例如模型可能返回：

    {
        "query": "辐射发射超标怎么办？",
        "top_k": "3"
    }

    这里会把字符串 "3" 转换为整数 3。
    """
    entry = TOOLS.get(tool_name)

    if entry is None:
        raise KeyError(f"未注册工具：{tool_name}")

    function = entry["func"]
    signature = inspect.signature(function)

    try:
        type_hints = get_type_hints(function)
    except (NameError, TypeError):
        type_hints = {}

    arguments: dict[str, Any] = {}

    for parameter_name, parameter in signature.parameters.items():
        if parameter_name in raw_arguments:
            value = raw_arguments[parameter_name]

            expected_type = type_hints.get(
                parameter_name,
                parameter.annotation,
            )

            try:
                if expected_type is int:
                    value = int(value)
                elif expected_type is float:
                    value = float(value)
                elif expected_type is str:
                    value = str(value)
            except (TypeError, ValueError):
                # 转换失败时保留原值，让实际函数抛出详细错误
                pass

            arguments[parameter_name] = value

        elif parameter.default is not inspect.Parameter.empty:
            arguments[parameter_name] = parameter.default

    return arguments


def execute_tool_call(tool_call: Any) -> str:
    """
    执行一个 Ollama 原生 ToolCall。

    tool_call 的结构大致为：

    tool_call.function.name
    tool_call.function.arguments
    """
    tool_function = tool_call.function
    tool_name = tool_function.name

    try:
        raw_arguments = tool_function.arguments or {}

        # 当前 Ollama Python SDK 通常返回 Mapping。
        # 这里兼容某些旧版本可能返回 JSON 字符串的情况。
        if isinstance(raw_arguments, str):
            raw_arguments = json.loads(raw_arguments)

        if not isinstance(raw_arguments, Mapping):
            raise TypeError(
                "tool arguments 必须是 JSON object。"
            )

        entry = TOOLS.get(tool_name)

        if entry is None:
            return (
                f"[工具调用错误] 未注册工具：{tool_name}"
            )

        arguments = coerce_arguments(
            tool_name=tool_name,
            raw_arguments=raw_arguments,
        )

        result = entry["func"](**arguments)

        return (
            f"[工具 {tool_name} 执行成功]\n"
            f"{result}"
        )

    except Exception as exc:  # noqa: BLE001
        return (
            f"[工具 {tool_name} 执行异常] "
            f"{type(exc).__name__}: {exc}"
        )


def run_agent(
    user_query: str,
    max_iter: int = MAX_ITER,
) -> tuple[str, list[Any]]:
    """
    Ollama Native Tool Calling Agent 主循环。

    流程：

    用户问题
       ↓
    ollama.chat(tools=NATIVE_TOOLS)
       ↓
    response.message.tool_calls
       ↓
    执行 Python 工具
       ↓
    role=tool 回填
       ↓
    再次调用模型
    """
    messages: list[Any] = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": user_query,
        },
    ]

    for step in range(1, max_iter + 1):
        print(
            f"\n------ 第 {step} 轮 LLM 调用 ------"
        )

        response: ChatResponse = ollama.chat(
            model=MODEL,
            messages=messages,
            tools=NATIVE_TOOLS,
            stream=False,
            think=THINK,
            options=OLLAMA_OPTIONS,
        )

        assistant_message = response.message

        print(
            "模型文本输出：",
            assistant_message.content,
        )

        tool_calls = list(
            assistant_message.tool_calls or []
        )

        print(
            "工具调用数量：",
            len(tool_calls),
        )

        # 必须保存完整的 assistant message。
        # 其中包含 tool_calls，不能只保存 content。
        messages.append(assistant_message)

        # 没有工具调用，说明这是最终回答。
        if not tool_calls:
            return (
                assistant_message.content or "",
                messages,
            )

        # 一个 assistant message 可以包含多个工具调用。
        for tool_call in tool_calls:
            print(
                "工具名称：",
                tool_call.function.name,
            )
            print(
                "工具参数：",
                tool_call.function.arguments,
            )

            result = execute_tool_call(tool_call)

            print(
                "工具结果：",
                result[:200],
            )

            # 原生 API 使用 tool_name 标记结果属于哪个工具。
            messages.append(
                {
                    "role": "tool",
                    "tool_name": tool_call.function.name,
                    "content": result,
                }
            )

    return (
        "已达到最大工具调用轮数，"
        "没有生成最终回答。",
        messages,
    )


TEST_QUERIES = [
    "辐射发射超标怎么办？",
    "你是什么模型？",
    "我的设备在开机时出现异常，怎么排查？",
    "请查询一下当前天气",
]


if __name__ == "__main__":
    print(f"当前模型：{MODEL}")
    print(
        "已注册原生工具：",
        list(TOOLS.keys()),
    )

    ollama_process = start_ollama_background()

    try:
        for index, query in enumerate(
            TEST_QUERIES,
            start=1,
        ):
            print(f"\n{'=' * 60}")
            print(f"测试用例 {index}：{query}")
            print(f"{'=' * 60}")

            answer, messages = run_agent(query)

            print("\n最终回答：")
            print(answer)

            print(
                "\n完整消息数量：",
                len(messages),
            )

    finally:
        # 只关闭本文件启动的 Ollama 服务。
        if ollama_process is not None:
            ollama_process.terminate()
            print("已关闭本次启动的 Ollama 服务。")
