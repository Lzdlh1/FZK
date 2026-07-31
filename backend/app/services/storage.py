"""对象存储封装。

沙箱环境使用本地文件系统替代 MinIO；
生产环境（有 MinIO 时）自动切换为 MinIO SDK。
"""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path
from typing import Any

from app.core.config import get_settings


def make_oid(filename: str | None = None, content_type: str | None = None) -> str:
    """生成对象 OID:uuid + 根据文件名/类型推断扩展名。"""
    ext = ""
    if filename:
        _, ext = os.path.splitext(filename)
    if not ext and content_type:
        ext_map = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
            "application/pdf": ".pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
        }
        ext = ext_map.get(content_type, "")
    return f"{uuid.uuid4().hex}{ext}"


class LocalStorage:
    """本地文件系统存储，接口与 MinioStorage 一致。"""

    def __init__(self, **kwargs: Any) -> None:
        settings = get_settings()
        self.bucket = kwargs.get("bucket") or settings.minio_bucket
        # 桌面打包模式:对象写入持久化数据目录(data/),跨启动保留;
        # 开发模式:沿用 /tmp,与历史行为一致。
        if getattr(sys, "frozen", False):
            base = settings.data_dir / "objects"
        else:
            base = Path(f"/tmp/{self.bucket}")
        self._base_dir = base
        self.ensure_bucket()

    def ensure_bucket(self) -> None:
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def upload_bytes(self, oid: str, data: bytes, content_type: str) -> None:
        filepath = self._base_dir / oid
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_bytes(data)

    def get_bytes(self, oid: str) -> tuple[bytes, str]:
        filepath = self._base_dir / oid
        data = filepath.read_bytes()
        ext = filepath.suffix.lower()
        ct_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }
        content_type = ct_map.get(ext, "application/octet-stream")
        return data, content_type

    def presigned_url(self, oid: str, expires: int = 3600) -> str:
        return f"/api/parse-jobs/drawing/{oid}"


class MinioStorage:
    """MinIO 存储的薄封装。"""

    def __init__(
        self,
        endpoint: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        bucket: str | None = None,
        secure: bool | None = None,
    ) -> None:
        from minio import Minio
        from minio.error import S3Error

        settings = get_settings()
        self.endpoint = endpoint or settings.minio_endpoint
        self.access_key = access_key or settings.minio_access_key
        self.secret_key = secret_key or settings.minio_secret_key
        self.bucket = bucket or settings.minio_bucket
        self.secure = secure if secure is not None else settings.minio_secure
        self._client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure,
        )

    def ensure_bucket(self) -> None:
        from minio.error import S3Error

        try:
            if not self._client.bucket_exists(self.bucket):
                self._client.make_bucket(self.bucket)
        except S3Error as exc:  # noqa: BLE001
            raise RuntimeError(f"MinIO bucket 初始化失败: {exc}") from exc

    def upload_bytes(self, oid: str, data: bytes, content_type: str) -> None:
        import io

        self._client.put_object(
            self.bucket,
            oid,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )

    def get_bytes(self, oid: str) -> tuple[bytes, str]:
        from urllib3.response import HTTPResponse

        resp: HTTPResponse = self._client.get_object(self.bucket, oid)
        try:
            data = resp.read()
            content_type = resp.headers.get("Content-Type", "application/octet-stream")
        finally:
            resp.close()
            resp.release_conn()
        return data, content_type

    def presigned_url(self, oid: str, expires: int = 3600) -> str:
        from datetime import timedelta

        return self._client.presigned_get_object(self.bucket, oid, expires=timedelta(seconds=expires))


_storage_singleton: LocalStorage | MinioStorage | None = None


def get_storage() -> LocalStorage | MinioStorage:
    """返回存储单例(读 config)。沙箱用本地文件系统，有 MinIO 时用 MinIO。"""
    global _storage_singleton
    if _storage_singleton is None:
        settings = get_settings()
        # 沙箱环境：endpoint 为 localhost 或 127.0.0.1 时用本地存储
        if settings.minio_endpoint in ("localhost", "127.0.0.1", "local"):
            _storage_singleton = LocalStorage()
        else:
            try:
                _storage_singleton = MinioStorage()
            except Exception:
                _storage_singleton = LocalStorage()
    return _storage_singleton


def reset_storage_singleton() -> None:
    """测试用:重置单例。"""
    global _storage_singleton
    _storage_singleton = None
