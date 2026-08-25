from __future__ import annotations

import argparse
from collections.abc import Callable
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from emc_backend.api.v1.router import api_router
from emc_backend.composition import AppContainer, build_container
from emc_backend.config import Settings

ContainerFactory = Callable[[Settings], AppContainer]


def create_app(
    *,
    settings: Settings | None = None,
    container_factory: ContainerFactory = build_container,
) -> FastAPI:
    """创建 FastAPI 应用，是测试和部署共用的应用工厂。

    ``settings or Settings.from_env()`` 是 Python 中常见的默认依赖写法：测试可
    显式传入配置，正式运行则读取环境。工厂模式避免模块导入时启动 Ollama。
    """

    resolved_settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        # yield 把生命周期分成启动和关闭两段：yield 前初始化，yield 后清理。
        container = container_factory(resolved_settings)
        await container.start()
        application.state.container = container
        try:
            yield
        finally:
            await container.close()

    application = FastAPI(
        title="EMC Fault Probe Agent API",
        version="0.1.0",
        description="Local-first API for EMC fault diagnosis Agent applications.",
        lifespan=lifespan,
    )
    application.include_router(api_router)
    # 生产构建存在时由同一个本地进程提供 Web 工作台；开发期仍可使用 Vite
    # 的 /api 代理获得热更新。API 路由先注册，因此不会被静态挂载遮蔽。
    web_dist = resolved_settings.project_root / "apps" / "web" / "dist"
    if web_dist.joinpath("index.html").is_file():
        application.mount("/", StaticFiles(directory=web_dist, html=True), name="web")
    return application


# ASGI 服务器和 PyCharm 可以直接导入 ``emc_backend.main:app``。
# 创建对象不会连接外部服务；资源初始化发生在上面的 lifespan 中。
app = create_app()


def run() -> None:
    """命令行与 PyCharm Script 运行入口。"""

    defaults = Settings.from_env()
    parser = argparse.ArgumentParser(description="Run EMC Fault Probe backend")
    parser.add_argument("--host", default=defaults.host)
    parser.add_argument("--port", type=int, default=defaults.port)
    parser.add_argument(
        "--reload",
        action="store_true",
        help="开发模式下监控 Python 文件并自动重启后端",
    )
    arguments = parser.parse_args()

    # reload 模式必须传导入字符串而不是 app 对象，Uvicorn 才能在子进程中重新
    # 导入模块。这也是 PyCharm 中获得后端热更新的关键。
    uvicorn.run(
        "emc_backend.main:app",
        host=arguments.host,
        port=arguments.port,
        reload=arguments.reload,
    )


if __name__ == "__main__":
    run()
