"""FZK 桌面应用入口(PyInstaller 打包目标)。

被 PyInstaller 打包成 exe 后,双击运行即:
1. 切到打包内 backend 目录(保证 ``app`` 包可导入)。
2. 调用 ``app.desktop.run_desktop()`` 启动后台服务 + 原生窗口。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _setup_path() -> None:
    """让 ``import app`` 在打包后仍可用。

    PyInstaller onefile:``__file__`` 在 _MEIPASS 内,backend 源码随包打入。
    one dir:同理。开发模式:本文件在仓库根,backend 在 ./backend。
    """
    here = Path(__file__).resolve().parent
    candidates = [here]
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        candidates.append(Path(sys._MEIPASS))  # type: ignore[attr-defined]
        candidates.append(Path(sys._MEIPASS) / "backend")  # type: ignore[attr-defined]
    candidates.append(here / "backend")
    for c in candidates:
        p = str(c)
        if p not in sys.path:
            sys.path.insert(0, p)


def main() -> int:
    _setup_path()
    # 桌面模式:写日志到 data 目录,便于排查问题
    try:
        from app.core.config import get_data_dir

        data_dir = get_data_dir()
        import logging

        logging.basicConfig(
            filename=str(data_dir / "fzk.log"),
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
    except Exception:  # noqa: BLE001
        pass

    from app.desktop import run_desktop

    return run_desktop()


if __name__ == "__main__":
    sys.exit(main())
