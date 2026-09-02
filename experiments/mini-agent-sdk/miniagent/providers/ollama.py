import ollama

from ..types import (
    Message,
    ModelRequest,
    ModelResponse,
)


class OllamaModel:
    def __init__(
        self,
        model_name: str,
        think: bool = False,
    ) -> None:
        self.model_name = model_name
        self.think = think

    def complete(
        self,
        request: ModelRequest,
    ) -> ModelResponse:
        # 这一段的写法是列表推导式，相当于下列代码:
        # ollama_messages = []
        #
        # for message in request.messages:
        #     ollama_messages.append(
        #         {
        #             "role": message.role,
        #             "content": message.content,
        #         }
        #     )

        ollama_messages = [
            {
                "role": message.role,
                "content": message.content,
            }
            for message in request.messages
        ]

        response = ollama.chat(
            model=self.model_name,
            messages=ollama_messages,
            stream=False,
            think=self.think,
        )

        assistant_message = Message(
            role="assistant",
            content=response.message.content or "",
        )

        return ModelResponse(
            message=assistant_message,
            # getattr 这段表示:
            # 尝试读取 response.done_reason, 如果不存在则返回 None
            finish_reason=getattr(
                response,
                "done_reason",
                None,
            ),
        )
