"""桌面应用启动器。

职责:
1. 在后台线程启动 uvicorn(FastAPI),承载 API + 前端静态文件。
2. 等待服务就绪后,用 pywebview 打开原生窗口(WebView2)加载本机服务。
3. 窗口关闭时优雅停止服务并退出进程。

仅在桌面打包模式下使用;Web/服务端部署仍走 ``uvicorn app.main:app``。
"""

from __future__ import annotations

import logging
import socket
import threading
import time
from typing import Any

import httpx
import uvicorn

logger = logging.getLogger("fzk.desktop")

# 窗口固定尺寸(可调整)
_WINDOW_WIDTH = 1440
_WINDOW_HEIGHT = 900
_WINDOW_TITLE = "线束工艺辅助卡系统"
_STARTUP_TIMEOUT = 30  # 秒


def _find_free_port(start: int = 18080, end: int = 18999) -> int:
    """在 [start, end) 范围内找一个可用端口,避免与其它实例冲突。"""
    for port in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"在 {start}-{end} 范围内无可用端口")


def _wait_for_server(url: str, timeout: int = _STARTUP_TIMEOUT) -> bool:
    """轮询健康检查接口,等待服务就绪。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = httpx.get(url, timeout=1.0)
            if r.status_code == 200:
                return True
        except Exception:  # noqa: BLE001
            pass
        time.sleep(0.2)
    return False


def _run_server(port: int, ready: threading.Event, server_ref: list[Any]) -> None:
    """后台线程:启动 uvicorn。``server_ref`` 用于回传 Server 对象以便关闭。"""
    config = uvicorn.Config(
        "app.main:app",
        host="127.0.0.1",
        port=port,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(config)
    server_ref.append(server)
    ready.set()  # 通知主线程 Server 已创建,可开始健康轮询
    try:
        server.run()
    except Exception:  # noqa: BLE001
        logger.exception("uvicorn 运行异常")


def run_desktop() -> int:
    """启动桌面应用,返回退出码。"""
    import webview  # 延迟导入,纯服务端环境无需安装 pywebview

    port = _find_free_port()
    base_url = f"http://127.0.0.1:{port}"
    health_url = f"{base_url}/api/health"

    server_ready_created = threading.Event()
    server_ref: list[Any] = []
    server_thread = threading.Thread(
        target=_run_server, args=(port, server_ready_created, server_ref), daemon=True
    )
    server_thread.start()
    server_ready_created.wait(timeout=5)

    logger.info("等待后端服务就绪 %s ...", health_url)
    if not _wait_for_server(health_url):
        print("[FZK] 后端启动超时,请重试。", flush=True)
        return 1

    # 窗口关闭回调:停止 uvicorn,让后台线程退出
    def _on_closed():
        if server_ref:
            server_ref[0].should_exit = True

    webview.create_window(
        _WINDOW_TITLE,
        base_url,
        width=_WINDOW_WIDTH,
        height=_WINDOW_HEIGHT,
        min_size=(1024, 700),
        on_closed=_on_closed,
    )
    # Windows 默认使用 EdgeChromium(WebView2,Win10/11 自带)
    webview.start()
    # 窗口关闭后,等待服务线程结束
    server_thread.join(timeout=5)
    return 0
