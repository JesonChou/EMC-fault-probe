# Ollama Native Tool Calling

这里保存从实验代码迁移出的 Ollama 适配器。它们是可复用组件，不是应用
运行入口，也不应直接创建 FastAPI 或桌面窗口。

正规运行链路为：

```text
用户问题
→ OllamaLLM.complete()
→ ToolCall
→ ToolRegistry / ToolExecutor
→ SearchCasesTool
→ OllamaEmbedder
→ ChromaCaseStore
→ ToolResult
→ OllamaLLM.complete()
→ 最终回答
```

## 应用入口边界

这些组件未来应在应用的 `composition.py` 中组装：

- 后端入口：`apps/backend/src/emc_backend/main.py`
- 后端组装：`apps/backend/src/emc_backend/composition.py`
- 桌面入口：`apps/desktop-agent/src/emc_desktop_agent/main.py`
- 桌面组装：`apps/desktop-agent/src/emc_desktop_agent/composition.py`

当前阶段只完成 Adapter、Tool 和 LocalRuntime，不提前实现前后端启动逻辑。

## 文件职责

- `client.py`：Ollama Chat 消息、ToolSpec 和 ToolCall 格式转换。
- `embeddings.py`：调用 Ollama embedding API。
- `health.py`：检查、启动和停止本地 Ollama 服务。

ChromaDB 适配器位于：

```text
integrations/vector_stores/chroma/store.py
```

目录名使用 `vector_stores` 而不是 `vector-stores`，因为 Python 模块名不能
包含连字符。
