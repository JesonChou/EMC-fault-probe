from dataclasses import dataclass
from typing import Literal

# Literal 表示只允许几个指定的字面值
# 编辑器可以发现有关 Role 的拼写错误
# 主要用于静态检查，不会自动在运行时拒绝错误角色
Role = Literal[
    "system",
    "user",
    "assistant",
]


# dataclass 主要用于简化类定义
# 其可以自动生成类初始化方法
# 等价于
# class Message:
#     def __init__(self, role: Role, message: str):
#         self.role = role
#         self.message = message

@dataclass
class Message:
    role: Role
    content: str


@dataclass
class ModelRequest:
    # message 是一个列表，列表中的每个元素都应该是 Message 类
    messages: list[Message]


@dataclass
class ModelResponse:
    message: Message
    finish_reason: str | None = None


# 类测试入口
if __name__ == "__main__":
    message = Message(
        role="system",
        content="Hello World!",
    )
    print(message)
