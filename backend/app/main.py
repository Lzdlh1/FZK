from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import Base, SessionLocal, engine

settings = get_settings()


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
