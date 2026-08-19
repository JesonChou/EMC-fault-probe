<h1 align = "center">EMC-fault-probe</h1>
<h1 align = "center">电磁兼容故障库（中文资料）</h1>
<h3 align="right">Records 1 tool calling</h3>
<p align="right">Begin: 2026.8.16</p>

<center>用于项目RAG化与Agent化改造学习记录</center>


<div style="page-break-after: always;"></div>

>   [!NOTE]
>
>   **文档背景**：本项目希望构建一个基于RAG（检索增强生成）与长期记忆系统的电磁兼容故障库 AGENT 助手。项目起源于BUAA 2系电磁兼容原理课程大作业，笔者想以此项目为抓手，逐步学习 AGNET 开发的相关技术知识，将该项目开发成一个完整的电磁兼容领域 AGENT 项目。笔者计划撰写系列文档来记录开发过程中所涉及到的背景知识、技术原理和具体技术细节，供笔者回顾复习，也希望可以帮助到与笔者同样的初学者。
>
>   本文档为系列文档第一篇，关于 AGENT 工具调用。

# 1. 背景知识简介

任何一种大语言模型（LLM）本质上都是语言模型，是不能对外部的物理世界造成影响的。要想让它完成网络搜索、文件读写等任务，就要为它装上工具，并告诉它有这些工具可用，并在合适的时候调用这些工具。

这些工具可以是一个函数、一个脚本或者一个软件——它们是在大模型出现之前就已经存在的各种各样的实用程序。而程序的运行往往依赖各种各样的变量和函数，函数运行需要一些参数。

大模型在获取到这些信息后，就可以知道在一个任务中该如何调用某个或者某类工具，在其决定需要调用工具时，将需要的参数返回回来；而 harness 程序校验、转换参数的数据类型后，执行工具，然后将这些结果返回给 LLM，LLM 根据工具执行结果来判断下一步需要做什么。这便是 tool calling 的简要流程。

因此我们需要做一些设计，让模型知道有什么工具、工具需要什么参数、该如何调用等等，并让模型在合适的时候调用工具，然后根据工具返回的结果决定下一步要做什么。

# 2. 项目 tool calling 设计

Tool calling 的实现方式主要有两种，一种是模型原生工具调用，另一种是系统 Prompt 工具调用。两者的区别如下：

| 对比条目 |                方式 A：原生 Function Calling                 |                   方式 B：Prompt 工具调用                    |
| :------: | :----------------------------------------------------------: | :----------------------------------------------------------: |
|   做法   | 请求时把 `tools=[{name, description, parameters}]` 传给 API，模型原生返回 `tool_calls` 结构化字段 | 把工具说明书写进 system 提示词，要求模型"需要时输出一个 JSON"^[1]^ |
| 格式保证 |         API 内部用约束解码（grammar），输出永远合法          |                    自己写解析器，必须容错                    |
| 模型兼容 |              deepseek-r1 对原生 tools 支持一般               |                     任何模型都能用^[2]^                      |
| 学习价值 |                    中（协议被 API 封装）                     |                  **高**（协议全在自己手里）                  |

------

**[1]** 这种方式利用了大模型的注意力机制——即对于开头和结尾的信息所赋予的权重最高，而对于中间信息会产生遗忘。将工具调用的说明拼入 system 放在对话的最开始，可以让模型记得工具调用的格式，尽可能保证传回参数的正确性。但是这种方式在工具越来越多的时候，会出现工具说明挤爆上下文的现象，导致业务可用上下文变短、后面的工具说明进入 Lost in the middle 区间等问题。因此方式 B 适合少工具、小任务，对于真正的业务来说不是一个合理的选择。但是在学习阶段，可以通过这个方式来学习 tool calling 协议。

**[2]** 虽然理论上方式 B 对任何模型都能用，但是在实际测试中笔者发现，不同的模型对自写协议的遵守能力不尽相同，且输出效果也不稳定。模型 `deepseek-r1` 系列很容易将思考过程中的文本或者工具报错本身作为需要解决的问题来进行推理，输出内容直接偏离用户 query；而同为千问系列的模型 `qwen2.5:7b` 和 `qwen3.5:9b-q4_K_M` ，前者容易出现重复输出，诸如==根据根据您您你 emo电磁兼容领域的知，11==的内容；而后者可以做到稳定输出。因此在实际的工程应用中，还是要采取支持原生 tools 的模型以及调用方法。

## 2.1 Prompt 协议调用

这一节，我们来实现一下方式 B 的路径。工具定义在[Codes/toolp.py](../Codes/toolp.py)，模型调用、解析器、校验器以及测试用例等放在[Codes/Toolp_Call_Test.py](../Codes/Toolp_Call_Test.py)。文件命名中的 `toolp` 指 `tool-prompt`，表示采用 Prompt 协议调用的方式实现 Tool Call。

### 2.1.1 `toolp.py` 工具定义

1.  TOOLS 工具注册表：

    将工具注册在 TOOLS 这一变量中。TOOLS 的数据类型为一个 `dict`，内部嵌套一个 `dict`，其结构为：

    ```python
    TOOLS = {
        "search_cases": {
            "name": "search_cases",
            "description": "...",
            "parameters": {...},
            "func": search_cases
        }
    }
    ```

    其中 `“search_cases”` 是函数名，每个函数名对应四个字段。因此 TOOLS 的数据结构应该为

    ```python
    TOOLS: dict[str, dict] = {} # 注册表: name -> {"name","description","parameters","func"}
    ```

    这样将每个函数注册进注册表，方便模型返回参数进行查表。

2.  将工具函数注册进 TOOLS 注册表：

    在这里，我们需要一个装饰器来将工具函数注册进注册表。函数定义如下：

    ```python
    def tool(name: str, description: str, parameters: dict):
        def decorator(func):
            TOOLS[name] = {
                "name": name,
                "description": description,
                "parameters": parameters, # JSON Schema
                "func": func,             # 真正的函数引用
            }
            return func
        return decorator
    ```

    该函数在使用时，使用一个 python 的语法糖：

    ```python
    @tool(
        "search_cases",
        "在电磁兼容故障库中检索故障词条。当用户描述故障现象、询问故障原因或解决方案时调用。"
        "返回匹配词条，每条含故障对象/故障现象/故障原因/解决方案/故障等级/发生频率。",
        SEARCH_CASES_SCHEMA,
    )
    def search_cases()
    	...
    ```

    第一个是函数名，数据类型为字符串；第二个参数是工具描述，数据类型也是字符串；而第三个参数是参数描述，也就是工具格式的 Schema。对于本项目中的第一个工具 `search_cases`，其 JSON Schema 为：

    ```python
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
    ```

    这段调用代码等价于：

    ```python
    def search_cases():
        ...
    
    search_cases = tool(
        "search_cases",
        "检索故障库",
        SEARCH_CASES_SCHEMA,
    )(search_cases)
    ```

    执行顺序为，先执行外层 `tool(...)` ，此时 `tool()` 还没有接收函数，只接收了工具的调用信息，返回内部函数 `decorator`：

    ```python
    decorator = tool(
        "search_cases",
        description,
        parameters,
    )
    ```

    然后 Python 创建 `search_cases` 函数对象，创建完成后，Python 会自动调用 `decorator(search_cases)` 。这个函数返回的是参数中的原函数，虽然原函数不变，但是通过这个过程， TOOLS 中被注册了对应的工具。

    因此在写法上，必须要写成

    ```python
    @tool(
        "search_cases",
        "检索故障库",
        SEARCH_CASES_SCHEMA,
    )
    def search_cases(query: str, top_k: int = 5):
        ...
    ```

    `@tool` 和 `search_ceses` 之间不能插入其它代码，两者也不能调换顺序，否则无效。

3.  转换注册表为字符串：

    将工具注册好后，我们需要将 TOOLS 中的 `dict` 数据类型转换为字符串，然后发送给模型。这就需要下面这个函数：

    ```python
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
    ```

    这个函数可以拆分为两部分：首先，`TOOLS.values()` 获取所有工具的内部字典；然后，`{k: v for k, v in entry.items() if k != "func"}` 复制字典中除了 `func` 之外的全部键值对。

    最后，这个函数的返回值采用了 `json.dumps` 这一函数，将 `schemas` 转换为 JSON 字符串，参数 `ensure_ascii=False` 表示保留中文，不转换成 `\uXXXX`；而 `indent=2` 表示使用两格缩进，让 JSON 更加易读。

4.  撰写搜索工具函数：

    我们可以在 [Codes/Embedding_Test.py](../Codes/Embedding_Test.py) 中进行数据 JSON 文件的向量化与数据库存储工作，在工具函数中只需要进行==对 `query` 进行向量化 $\rightarrow$ 提取数据库中的条目并与 `query` 的向量化进行余弦相似度比较 $\rightarrow$ 取最相似的若干条 `(Top-K)`== 的工作。完整的搜索工具函数如下：

    ```python
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
    ```

    `query` 向量化和余弦相似度的实现方法和函数，参见本文件内部的 `embed_text` 、`cosine_similarity` 函数，以及相关功能的测试文件 [Codes/Embedding_Test.py](../Codes/Embedding_Test.py)。

### 2.1.2 `Toolp_Call_Test.py` 工具调用测试

`Toolp_Call_Test.py` 负责完成模型调用、工具调用 JSON 的解析、参数校验、工具执行以及测试。它从 `toolp.py` 中导入 `TOOLS`、`tool_schemas_text` 和 `search_cases`。其中，导入 `toolp` 模块时，`search_cases` 函数上的 `@tool` 装饰器会自动执行，将工具注册进 `TOOLS` 注册表。

1.  配置模型和工具说明书：

    文件开头定义了模型名称和 Agent 工具调用的最大循环次数：

    ```python
    MODEL = "qwen3.5:9b-q4_K_M"
    MAX_ITER = 5
    INCLUDE_TOOL_SCHEMAS = True
    ```

    `MODEL` 是本地 Ollama 中实际使用的模型；`MAX_ITER` 用于限制一次用户请求最多进行多少轮“模型调用 $\rightarrow$ 工具执行 $\rightarrow$ 结果回填”，避免模型在工具调用过程中无限循环。`INCLUDE_TOOL_SCHEMAS` 是一个对照实验开关，为 `True` 时把工具说明书加入 system message，为 `False` 时只保留人设和基本规则，此时模型无法知道可用工具的名称和参数。

    system prompt 对模型提出了三条要求：需要查询故障库时输出工具调用 JSON；工具调用时只输出指定格式的 JSON；可以直接回答时输出普通文本。组装 system message 的函数如下：

    ```python
    def build_system_message() -> str:
        """组装 system 消息：人设 + 工具使用规则 + 工具说明书"""
        content = SYSTEM_PROMPT
        if INCLUDE_TOOL_SCHEMAS:
            content += "\n\n可用工具列表：\n" + tool_schemas_text()
        return content
    ```

    这样做的好处是工具说明书的生成和 system prompt 的组装彼此分离。工具数量或工具参数发生变化时，只需要修改工具注册代码，`tool_schemas_text()` 就会重新生成发送给模型的 JSON 文本。

2.  Ollama 服务管理：

    本测试使用 Ollama 的 HTTP 服务进行模型调用。为了避免在服务已经启动时重复启动进程，先通过访问 `/api/tags` 判断服务是否可用：

    ```python
    def is_ollama_serving() -> bool:
        """探测 Ollama HTTP 服务是否已在运行（访问 /api/tags）。"""
        try:
            urllib.request.urlopen(
                "http://127.0.0.1:11434/api/tags",
                timeout=2,
            )
            return True
        except OSError:
            return False
    ```

    如果服务没有运行，`start_ollama_background()` 会使用 `subprocess.Popen` 在后台启动 `ollama serve`，并将输出写入 `ollama_serve.log`。函数最多等待 15 秒，直到 HTTP 服务可以访问。测试结束时，只有本次测试自行启动的服务才会被关闭，原本已经运行的 Ollama 服务不会受到影响。

3.  解析模型返回的工具调用 JSON：

    模型理想情况下应当返回如下格式的内容：

    ```json
    {
      "name": "search_cases",
      "arguments": {
        "query": "辐射发射超标怎么办？"
      }
    }
    ```

    但是，Prompt 协议调用并不能像原生 Function Calling 一样保证模型输出永远是合法 JSON。部分模型可能在 JSON 前后输出解释性文字，思考模型还可能在思考过程中生成多个 JSON 片段。因此不能直接使用 `json.loads(reply)` 要求整个回复都是 JSON，而是使用 `JSONDecoder.raw_decode` 从每一个左花括号开始尝试解析：

    ```python
    def parse_tool_call(reply: str) -> dict | None:
        decoder = json.JSONDecoder()
        result = None

        for index, character in enumerate(reply):
            if character != "{":
                continue
            try:
                candidate, _ = decoder.raw_decode(reply[index:])
            except json.JSONDecodeError:
                continue
            if (
                isinstance(candidate, dict)
                and "name" in candidate
                and "arguments" in candidate
            ):
                result = candidate
        return result
    ```

    `raw_decode` 只解析从当前位置开始的一个 JSON 对象，解析完成后允许后面继续存在其他文本。函数会保留最后一个同时包含 `name` 和 `arguments` 字段的字典；如果没有找到符合要求的对象，就返回 `None`。在 Agent 主循环中，返回 `None` 表示模型已经给出了最终回答，而不是工具调用。

4.  校验和转换工具参数：

    模型返回的参数属于协议层数据，不能直接假定它们一定符合 Python 函数的参数类型。例如，模型可能将整数 `5` 输出为字符串 `"5"`。`coerce_arguments()` 使用 `inspect.signature()` 读取工具函数的签名，根据参数注解进行类型转换，并在缺少参数时使用函数定义中的默认值：

    ```python
    def coerce_arguments(call: dict) -> dict:
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
                    except (TypeError, ValueError):
                        args[pname] = value
                elif param.annotation is float:
                    try:
                        args[pname] = float(value)
                    except (TypeError, ValueError):
                        args[pname] = value
                elif param.annotation is str:
                    args[pname] = str(value)
                else:
                    args[pname] = value
            elif param.default is not inspect.Parameter.empty:
                args[pname] = param.default
        return args
    ```

    这里的校验重点是将协议层的 JSON 字段转换为函数层可以接收的 `dict`。如果参数无法转换，则暂时保留原值，交由实际工具函数报错；这样可以把具体的错误信息回填给模型，而不是在解析阶段直接中止整个 Agent。

5.  执行工具并处理异常：

    `execute_tool()` 根据工具名查询 `TOOLS` 注册表，调用其中保存的真实函数引用，并把执行结果统一转换成字符串：

    ```python
    def execute_tool(call: dict) -> str:
        try:
            args = coerce_arguments(call)
            func = TOOLS[call["name"]]["func"]
            result = func(**args)
            return f"[工具 {call['name']} 执行成功]\n{result}"
        except KeyError as e:
            return f"[工具调用错误] {e}。请检查工具名是否正确，或改用其他方式回答。"
        except Exception as e:
            return f"[工具执行异常] {type(e).__name__}: {e}"
    ```

    工具不存在、参数错误以及工具内部异常都会被转换为文本，而不会直接让程序崩溃。因为大语言模型只能读取消息内容，所以无论工具成功还是失败，最终都需要以字符串形式回填到对话中，让模型自行决定是重新调用、改用其他方式，还是向用户说明无法完成查询。

6.  Agent 主循环：

    `run_agent()` 实现了最小的 Agent 循环，执行流程为：

    ```text
    用户问题
      ↓
    调用 LLM
      ↓
    解析工具调用 JSON
      ├─ 没有解析到工具调用 → 返回模型文本作为最终回答
      └─ 解析到工具调用
            ↓
         校验参数并执行工具
            ↓
         以 role="tool" 回填执行结果
            ↓
         再次调用 LLM
    ```

    对应的核心代码如下：

    ```python
    def run_agent(user_query: str, max_iter: int = MAX_ITER) -> tuple[str, list[dict]]:
        messages = [{"role": "system", "content": build_system_message()}]
        messages.append({"role": "user", "content": user_query})

        for step in range(1, max_iter + 1):
            reply = ollama.chat(
                model=MODEL,
                messages=messages,
            )["message"]["content"]
            messages.append({"role": "assistant", "content": reply})

            call = parse_tool_call(reply)
            if call is None:
                return reply, messages

            result = execute_tool(call)
            messages.append({"role": "tool", "content": result})

        return "已达最大迭代次数，请修改或简化问题重试。", messages
    ```

    每一轮模型回复都要先追加到 `messages`，这样模型在下一轮能够看到自己的工具调用内容。工具执行结果则以独立的 `role="tool"` 消息追加，模型可以据此生成最终回答或发起下一次工具调用。当模型输出普通文本时，循环立即结束；如果达到 `MAX_ITER` 仍然没有得到最终文本，则返回最大迭代次数提示。

7.  四类测试用例：

    文件的测试入口设置了四类问题，用于分别观察正常调用、无需调用、模糊问题和错误工具名的处理结果：

    ```python
    test_queries = [
        "辐射发射超标怎么办？",              # 需要检索，应触发 search_cases
        "你是什么模型？",                  # 纯知识问题，不应触发工具
        "我的设备在开机时出现异常，怎么排查？", # 模糊问题，观察模型判断
        "请调用工具 get_weather 查天气",    # 工具不存在，验证容错降级
    ]
    ```

    第一个问题用于验证从故障描述到向量检索的完整链路；第二个问题用于验证模型在不需要外部资料时可以直接回答；第三个问题用于观察 system prompt 对模型工具选择的影响；第四个问题用于验证未知工具名会被捕获并转化为模型可读的错误文本。

## 2.2 Ollama 原生工具调用

`//TODO`
