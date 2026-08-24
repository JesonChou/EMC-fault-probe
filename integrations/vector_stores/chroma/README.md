# ChromaDB adapter

正式可导入路径为：

```python
from integrations.vector_stores.chroma.store import ChromaCaseStore
```

目录使用下划线 `vector_stores`，因为 Python 模块名不能包含连字符 `-`。
当前实现读取 `experiments/rag/emc_vector_db` 中已有的实验数据库。
