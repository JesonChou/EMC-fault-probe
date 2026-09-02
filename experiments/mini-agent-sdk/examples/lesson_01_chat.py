from miniagent import (
    Message,
    Model,
    ModelRequest,
)
from miniagent.providers.ollama import OllamaModel


def run_chat(model: Model) -> None:
    request = ModelRequest(
        messages=[
            Message(
                role="system",
                content="你是一个强有力的AI Agent助手。",
            ),
            Message(
                role="user",
                content=(
                    "你是谁？请用一句话解释"
                    "什么是电磁兼容。"
                ),
            ),
        ]
    )

    response = model.complete(request)

    # assert 是 python 关键字，进行最简单的运行验证
    # 下面的验证内容是，响应的角色必须是 assistant
    # 且响应文本不能是空字符串
    # 如果条件不成立，程序会抛出
    # AssertionError
    assert response.message.role == "assistant"
    assert response.message.content

    print(
        "返回消息类型：",
        type(response.message).__name__,
    )
    print(
        "消息角色：",
        response.message.role,
    )
    print(
        "终止原因：",
        response.finish_reason,
    )
    print(
        "模型回答：",
        response.message.content,
    )


if __name__ == "__main__":
    ollama_model = OllamaModel(
        model_name="qwen3.5:9b-q4_K_M",
        think=False,
    )

    run_chat(ollama_model)
