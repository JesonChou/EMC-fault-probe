import inspect
import json
import subprocess
import time
import urllib.request

import ollama

# import 工具模块即触发 @tool 装饰器 → TOOLS 注册表自动填好
from toolp import TOOLS, tool_schemas_text

### 配置

MODEL = "qwen3.5:9b-q4_K_M"
# MODEL = "qwen2.5:7b"
# MODEL = "deepseek-r1:7b"
MAX_ITER = 5          # 工具循环上限

# 对照实验开关： True = system 带工具说明书；False = 去掉说明书，模型将不再调用工具
INCLUDE_TOOL_SCHEMAS = True

SYSTEM_PROMPT = (
    "你是一个电磁兼容领域的专家，负责解答电磁兼容故障问题。\n"
    "规则：\n"
    "1. 当用户的问题需要查询故障库资料时，你必须输出工具调用 JSON；\n"
    "2. 工具调用 JSON 格式：{\"name\": \"工具名\", \"arguments\": {参数}}，"
    "只输出这个 JSON，不要输出其他任何内容；\n"
    "3. 当你可以直接回答时，正常输出回答文本，不要输出 JSON。"
)

def build_system_message() -> str:
    """组装 system 消息：人设 + 工具使用规则 + 工具说明书"""
    content = SYSTEM_PROMPT
    if INCLUDE_TOOL_SCHEMAS:
        content += "\n\n可用工具列表：\n" + tool_schemas_text()
    return content


### Ollama 服务管理

def is_ollama_serving() -> bool:
    """探测 Ollama HTTP 服务是否已在运行（访问 /api/tags）。"""
    try:
        urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=2)
        return True
    except OSError:  # 连接失败/超时均属 OSError 家族
        return False


def start_ollama_background():
    """确保 Ollama serve 在后台运行；本来就在运行则返回 None。"""
    if is_ollama_serving():
        print("Ollama 服务已在运行")
        return None
    with open("ollama_serve.log", "a", encoding="utf-8") as log:
        process = subprocess.Popen(
            ["ollama", "serve"],
            stdout=log,
            stderr=subprocess.STDOUT,
        )
    print(f"Ollama serve 已启动，进程ID: {process.pid}（日志见 ollama_serve.log）")
    for _ in range(30):
        if is_ollama_serving():
            print("Ollama 服务就绪")
            return process
        time.sleep(0.5)
    print("警告：Ollama 服务 15 秒内未就绪，请检查 ollama_serve.log")
    return process


### 解析器，从模型回复中提取工具调用json

def parse_tool_call(reply: str) -> dict | None:
    """从模型回复中提取工具调用 JSON

    使用 JSONDecoder.raw_decode 从头扫描每一个 '{'，保留最后一个解析成功
    且含 name/arguments 的对象 —— 这样思考过程中的干扰文本会被跳过
    主要用于过滤 deepseek-r1 这样的思考模型输出的思考文本

    这里传入的参数 reply 是模型返回的回复

    raw_decode 是 json.JSONDecoder 的方法，用来解析 JSON。
    和常用的 json.load 区别是
    json.load 要求整个字符串是合法 JSON， 否则报错
    而 raw_decode 只要求字符串开头是合法 JSON， 解析完一个 JSON 就停
    允许后面有别的内容
    返回一个包含两个元素的元组：

    (obj, end_index)

    第一个元素为解析出来的 Python 对象，通常是 dict 或者 list
    第二个元素是 JSON 解析结束的位置，在字符串中的下标

    reply[index:] 是字符串切片，取 reply 从下标 index 开始到末尾的字符串

    candidate, _ = ...
    元组解包，将 decoder.raw_decode 解析出来的 JSON 对象和结束下标赋值给两个变量
    因为下标不需要，所以用 _ 这个约定俗成的丢弃变量承接
    """
    decoder = json.JSONDecoder()
    result = None

    for index, character in enumerate(reply):
        if character != "{":
            continue
        try:
            candidate, _ = decoder.raw_decode(reply[index:])
        except json.JSONDecodeError:
            continue
        if(
            # isinstance 是 Python 的类型检查，判断 candidate 这个变量是不是一个 dict
            # 需要这个检查是因为 raw_decode 能解析出任意 JSON 类型，不一定是 dict，
            # 可能是字符串、列表、数字或者 None
            # 该函数的第二个参数可以传元组，一次检查多个类型
            # 例如 isinstance(x, (dict, list))   # x 是字典或列表都可以
            isinstance(candidate, dict)
            and "name" in candidate
            and "arguments" in candidate
        ):
            result = candidate
    return result


### 校验器，参数类型强制转换 + 缺字段补充默认值

def coerce_arguments(call: dict) -> dict:
    """把模型给的 arguments 参数校正成函数期望的类型，缺字段补默认值

    模型输出的 JSON 里 "5" 可能是字符串，而函数签名要 int
    这一步将协议层的数据转化为函数层的参数
    """

    # 校验 name 字段
    name = call.get("name")
    entry = TOOLS.get(name)
    if entry is None:
        raise KeyError("工具不存在")

    func = entry["func"]
    sig = inspect.signature(func)
    raw = dict(call.get("arguments") or {})

    args = {}
    for pname, param in sig.parameters.items():
        if pname in raw:
            value = raw[pname]
            if param.annotation is int:
                try:
                    args[pname] = int(value)
                except(TypeError, ValueError):
                    args[pname] = value # 如果无法转换，那么原样传入函数，让函数自己报错
            elif param.annotation is float:
                # 函数签名声明为 float, 则转换为 float
                try:
                    args[pname] = float(value)
                except(TypeError, ValueError):
                    args[pname] = value
            elif param.annotation is str:
                # 函数签名声明为 str, 则转换为 str
                args[pname] = str(value)
            else:
                args[pname] = value
        elif param.default is not inspect.Parameter.empty:
            args[pname] = param.default # 缺失字段用函数默认值
    return args


### 执行器: 查询注册表、调用函数、异常转化为文本

def execute_tool(call: dict) -> str:
    """执行一次工具调用，任何异常都转成文本回填给模型

    返回内容始终是字符串，因为大语言模型只能读取字符串
    """
    try:
        # 校验模型参数，输出一个 dict.
        # args的类型为dict, 包含校验出来的函数参数
        args = coerce_arguments(call)
        # func = TOOLS[call["name"]["func"]]
        # func = TOOLS[call["name"]]
        # entry = TOOLS[call["name"]]
        # func = entry["func"]


        func = TOOLS[call["name"]]["func"]
        result = func(**args)
        return f"[工具 {call['name']} 执行成功]\n{result}"
    except KeyError as e:
        return f"[工具调用错误] {e}。请检查工具名是否正确，或改用其他方式回答。"
    except Exception as e: # noqa: BLE001 - 工具内部错误也要回填，让模型决定重试或者放弃
        return f"[工具执行异常] {type(e).__name__}: {e}"


### Agent 主循环：消息 -> LLM -> 解析 -> 执行 -> 回填 -> 再生成

def run_agent(user_query: str, max_iter: int = MAX_ITER) -> tuple[str, list[dict]]:
    """最小agent loop
    返回最终回答
    """
    messages = [{"role": "system", "content": build_system_message()}]
    messages.append({"role": "user", "content": user_query})
    for step in range(1, max_iter + 1):
        print(f"\n------ 第 {step} 轮 LLM 调用 ------")
        reply = ollama.chat(model = MODEL, messages = messages)["message"]["content"]
        print("模型原始输出：", reply)

        messages.append({"role": "assistant", "content": reply})

        call = parse_tool_call(reply) # 调用解析器
        if call is None:
            return reply, messages

        print(f"解析到工具调用：{call}")
        result = execute_tool(call)
        print(f"工具执行结果（截断显示）：{result[:200]}...")

        # 回填：以独立的 tool 字段告诉模型这是工具返回
        messages.append({"role": "tool", "content": result})

    return "已达最大迭代次数，请修改或简化问题重试。", messages


### 测试入口，四类用例

if __name__ == "__main__":
    print(MODEL)
    test_queries = [
        "辐射发射超标怎么办？",                       # ① 需要检索 → 应触发 search_cases
        "你是什么模型？",                           # ② 纯知识问题 → 不应触发工具
        "我的设备在开机时出现异常，怎么排查？",      # ③ 模糊问题 → 观察是否调用/如何调用
        "请调用工具 get_weather 查天气", # ④ 工具不存在 → 验证容错降级
    ]

    ollama_process = start_ollama_background()
    try:
        for i, q in enumerate(test_queries, 1):
            print(f"\n{'=' * 60}\n测试用例 {i}：{q}\n{'=' * 60}")
            answer, messages = run_agent(q)
            print(f"\n最终回答：{answer}")
            print(f"\n本轮完整消息条数：{len(messages)}")
    finally:
        # 只有本次启动的 serve 进程才需要关闭；服务原本就在运行（None）时绝不能动它
        if ollama_process is not None:
            ollama_process.terminate()
            print("已关闭本次启动的 Ollama serve 进程")
