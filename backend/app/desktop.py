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
import traceback
from typing import Any

import httpx
import uvicorn

logger = logging.getLogger("fzk.desktop")

# 窗口固定尺寸(可调整)
_WINDOW_WIDTH = 1440
_WINDOW_HEIGHT = 900
_WINDOW_TITLE = "线束工艺辅助卡系统"
_STARTUP_TIMEOUT = 60  # 秒(打包后首次启动 import 较慢,放宽)


def _find_free_port(start: int = 13161, end: int = 13260) -> int:
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
            # trust_env=False: 忽略系统代理变量(HTTP_PROXY/HTTPS_PROXY),
            # 避免公司环境把 127.0.0.1 本机请求强制走代理导致健康检查失败。
            r = httpx.get(url, timeout=1.0, trust_env=False)
            if r.status_code == 200:
                return True
        except Exception:  # noqa: BLE001
            pass
        time.sleep(0.3)
    return False


def _show_error_dialog(message: str) -> None:
    """在 Windows 上弹出原生消息框显示错误(GUI 模式无控制台,这是唯一可见途径)。"""
    logger.error("启动失败: %s", message)
    try:
        import ctypes

        # MB_ICONERROR=0x10 | MB_OK=0x0
        ctypes.windll.user32.MessageBoxW(0, message, "FZK 启动失败", 0x10)
    except Exception:  # noqa: BLE001
        # 非 Windows 或无 GUI:退化为 stderr
        import sys

        print(message, file=sys.stderr, flush=True)


def _write_crash_file(message: str) -> None:
    """把崩溃信息写到 exe 同级 crash.txt,便于用户反馈。"""
    try:
        import sys
        from pathlib import Path

        if getattr(sys, "frozen", False):
            target = Path(sys.executable).resolve().parent / "crash.txt"
        else:
            target = Path.cwd() / "crash.txt"
        target.write_text(message, encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass


def _run_server(
    port: int,
    ready: threading.Event,
    server_ref: list[Any],
    startup_error: list[str],
) -> None:
    """后台线程:启动 uvicorn。

    ``server_ref`` 用于回传 Server 对象以便关闭。
    ``startup_error`` 用于回传启动阶段(含 app import)的异常 traceback。
    """
    # 先显式 import app,把 import 期错误捕获到 startup_error(而不是被
    # uvicorn 内部 logger 吞掉、在 GUI 模式下无处可看)。
    try:
        import app.main  # noqa: F401  触发完整 import 图,提前暴露错误
        logger.info("app.main 导入成功")
    except Exception:  # noqa: BLE001
        tb = traceback.format_exc()
        startup_error.append(tb)
        logger.error("app.main 导入失败:\n%s", tb)
        ready.set()  # 让主线程往下走,触发超时分支并显示错误
        return

    config = uvicorn.Config(
        "app.main:app",
        host="127.0.0.1",
        port=port,
        log_level="info",
        access_log=False,
    )
    # 让 uvicorn 的日志也进 root(写进 fzk.log)
    for uv_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uv_log = logging.getLogger(uv_name)
        uv_log.handlers = []  # 去掉 uvicorn 自带 handler,完全交给 root
        uv_log.propagate = True

    try:
        server = uvicorn.Server(config)
        server_ref.append(server)
        ready.set()  # 通知主线程 Server 已创建,可开始健康轮询
        server.run()
    except Exception:  # noqa: BLE001
        tb = traceback.format_exc()
        startup_error.append(tb)
        logger.error("uvicorn 运行异常:\n%s", tb)


def run_desktop() -> int:
    """启动桌面应用,返回退出码。"""
    import webview  # 延迟导入,纯服务端环境无需安装 pywebview

    port = _find_free_port()
    base_url = f"http://127.0.0.1:{port}"
    health_url = f"{base_url}/api/health"

    server_ready_created = threading.Event()
    server_ref: list[Any] = []
    startup_error: list[str] = []
    server_thread = threading.Thread(
        target=_run_server,
        args=(port, server_ready_created, server_ref, startup_error),
        daemon=True,
    )
    server_thread.start()
    server_ready_created.wait(timeout=10)

    logger.info("等待后端服务就绪 %s ...", health_url)
    if not _wait_for_server(health_url):
        # 启动失败:把后端 import / 运行错误显示给用户
        if startup_error:
            err = startup_error[-1]
            msg = f"后端启动失败,错误详情:\n\n{err[:3000]}"
        else:
            msg = (
                f"后端在 {_STARTUP_TIMEOUT} 秒内未就绪({health_url} 无响应)。\n"
                "可能原因:端口被占用、依赖加载失败或安全软件拦截。\n"
                "请查看 exe 同级 fzk.log / crash.txt 获取详情。"
            )
        _write_crash_file(msg + "\n\n" + "\n\n".join(startup_error))
        _show_error_dialog(msg)
        return 1

    # pywebview 6.x:create_window 不再有 on_closed 参数,
    # 改用返回的 window 对象的事件机制注册关闭回调。
    window = webview.create_window(
        _WINDOW_TITLE,
        base_url,
        width=_WINDOW_WIDTH,
        height=_WINDOW_HEIGHT,
        min_size=(1024, 700),
    )

    def _on_closed():
        if server_ref:
            server_ref[0].should_exit = True

    # closing 事件:用户点关闭按钮时触发,此时还能在窗口线程里做清理
    window.events.closing += _on_closed

    # Windows 默认使用 EdgeChromium(WebView2,Win10/11 自带)
    webview.start()
    # 窗口关闭后,等待服务线程结束
    server_thread.join(timeout=5)
    return 0
