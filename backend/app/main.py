import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import api_router
from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import Base, SessionLocal, engine

settings = get_settings()


def _resolve_frontend_dist() -> Path | None:
    """定位前端构建产物目录。

    优先级:
    1. PyInstaller 打包:``_MEIPASS/frontend_dist``
    2. 开发模式:``<repo>/frontend/dist``
    3. exe 同级 ``frontend_dist``(便于 onedir 手动放置)
    找不到返回 None(纯 API 模式,前端走 vite dev)。
    """
    candidates: list[Path] = []
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        candidates.append(Path(sys._MEIPASS) / "frontend_dist")  # type: ignore[attr-defined]
    candidates.append(Path(__file__).resolve().parents[2] / "frontend" / "dist")
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).resolve().parent / "frontend_dist")
    for c in candidates:
        if (c / "index.html").is_file():
            return c
    return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            from app.models.user import User

            if db.query(User).first() is None:
                admin = User(name="admin", password_hash=hash_password("admin"), role="admin")
                db.add(admin)
                db.commit()

            from app.services.seed import seed_preset_rules

            seed_preset_rules(db)
        finally:
            db.close()
    except Exception as exc:  # noqa: BLE001
        print(f"[startup] 数据库初始化跳过: {exc}")
    # MinIO bucket 自检(失败不阻断启动)
    try:
        from app.services.storage import get_storage

        get_storage().ensure_bucket()
    except Exception as exc:  # noqa: BLE001
        print(f"[startup] MinIO bucket 初始化跳过: {exc}")
    yield


app = FastAPI(title="线束工艺辅助卡系统", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# 前端静态资源挂载(桌面打包 / 单体部署模式)
# 找到 dist 目录时:挂载 /assets 等,并对所有非 /api、非已存在文件请求
# 回退到 index.html(SPA 路由)。找不到 dist 时跳过,保持纯 API 模式。
# ---------------------------------------------------------------------------
_frontend_dist = _resolve_frontend_dist()
if _frontend_dist is not None:
    _assets_dir = _frontend_dist / "assets"
    if _assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="assets")

    @app.get("/{full_path:path}")
    def _spa_fallback(full_path: str):  # noqa: ANN202
        # /api/* 已由上方路由处理,此处不会命中(路由顺序:API 先注册)
        candidate = _frontend_dist / full_path
        if full_path and candidate.is_file():
            return FileResponse(str(candidate))
        return FileResponse(str(_frontend_dist / "index.html"))
