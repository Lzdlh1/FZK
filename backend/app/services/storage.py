"""MinIO 对象存储封装。

仅做 MVP 所需的最小操作:bucket 自检、字节上传/下载、预签名 URL。
所有方法均为同步(MinIO SDK 本身是同步的);异步调用方在线程池中执行即可。
"""

from __future__ import annotations

import os
import uuid
from typing import Any

from minio import Minio
from minio.error import S3Error
from urllib3.response import HTTPResponse

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
        """返回 (bytes, content_type)。"""
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


_storage_singleton: MinioStorage | None = None


def get_storage() -> MinioStorage:
    """返回单例 MinioStorage(读 config)。"""
    global _storage_singleton
    if _storage_singleton is None:
        _storage_singleton = MinioStorage()
    return _storage_singleton


def reset_storage_singleton() -> None:
    """测试用:重置单例。"""
    global _storage_singleton
    _storage_singleton = None
