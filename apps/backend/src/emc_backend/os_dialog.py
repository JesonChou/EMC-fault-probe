from __future__ import annotations

from pathlib import Path


def pick_directory(initial_path: str) -> str | None:
    """在运行后端的本机打开目录选择器。

    Web File System Access API 不会暴露本地绝对路径，而 Agent 的工作区服务
    需要真实路径。后端只监听 loopback，因此由本机进程弹出系统对话框既能
    保留浏览器前端，也能得到可供 RAG/工具读取的路径。
    """

    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError as exc:  # pragma: no cover - 取决于 Python 发行版
        raise RuntimeError("当前 Python 环境不包含系统目录选择器") from exc

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        selected = filedialog.askdirectory(
            parent=root,
            title="选择 EMC Agent 工作区",
            initialdir=initial_path,
            mustexist=True,
        )
    finally:
        root.destroy()
    return str(Path(selected).resolve()) if selected else None
