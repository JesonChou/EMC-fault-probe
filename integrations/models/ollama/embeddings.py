from __future__ import annotations

from ollama import AsyncClient


class OllamaEmbedder:
    """使用 Ollama embedding 模型实现 TextEmbedder 端口。"""

    def __init__(
        self,
        *,
        model: str,
        client: AsyncClient | None = None,
        host: str | None = None,
    ) -> None:
        self._model = model
        self._owns_client = client is None
        self._client = client if client is not None else AsyncClient(host=host)

    async def close(self) -> None:
        """关闭由本 Adapter 自己创建的 AsyncClient。"""

        if self._owns_client:
            await self._client.close()

    async def embed(self, text: str) -> list[float]:
        """调用 Ollama，把一段文本转换成一个浮点向量。"""

        response = await self._client.embed(
            model=self._model,
            input=text,
        )

        # embed() 支持一次传入多段文本，所以返回值是二维数组：
        # embeddings[文本序号][向量维度]。这里只传入一段文本，因此取 [0]。
        if not response.embeddings:
            raise RuntimeError("Ollama embedding 响应中没有向量。")

        return [float(value) for value in response.embeddings[0]]
