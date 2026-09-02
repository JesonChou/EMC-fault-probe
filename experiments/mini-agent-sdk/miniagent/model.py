from typing import Protocol

from .types import ModelRequest, ModelResponse

# Protocol 描述一个对象应该具有哪些方法
# 规定一个 Model 类必须提供 complete(request) -> ModelResponse 方法
# 也可以使用父类继承，但是稍微有些麻烦。使用 Protocol, 只要方法符合约定就可以视为 Model 类
# 这更适合以后接入 FakeModel 和第三方适配器

class Model(Protocol):
    def complete(
        self,
        request: ModelRequest,
    ) -> ModelResponse:
        ...
