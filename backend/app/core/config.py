import os
import sys
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _is_frozen() -> bool:
    """是否运行在 PyInstaller 打包环境中。"""
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def get_data_dir() -> Path:
    """返回持久化数据目录。

    桌面打包模式下,exe 旁的 ``data/`` 目录(可写、跨启动保留)。
    开发/服务端模式下返回当前工作目录。
    """
    if _is_frozen():
        # onefile: sys.executable 是 exe 本体;onefile 解包目录是只读的 _MEIPASS,不能用
        base = Path(sys.executable).resolve().parent / "data"
    else:
        base = Path.cwd()
    base.mkdir(parents=True, exist_ok=True)
    return base


class Settings(BaseSettings):
    database_url: str = "sqlite:///./harness.db"
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 10080
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "harness"
    minio_secure: bool = False
    cors_origins: str = "http://localhost:5173,http://localhost:8080"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def data_dir(self) -> Path:
        return get_data_dir()


@lru_cache
def get_settings() -> Settings:
    """构造 Settings,桌面打包模式下强制 SQLite + 本地存储 + 数据目录持久化。"""
    if _is_frozen():
        data_dir = get_data_dir()
        db_path = data_dir / "harness.db"
        os.environ.setdefault("DATABASE_URL", f"sqlite:///{db_path}")
        os.environ.setdefault("MINIO_ENDPOINT", "local")
        os.environ.setdefault("MINIO_BUCKET", "harness")
        os.environ.setdefault("CORS_ORIGINS", "*")
        os.environ.setdefault("JWT_SECRET", "fzk-desktop-default-secret")
    return Settings()
