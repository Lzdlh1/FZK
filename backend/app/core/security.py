from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings

# 直接使用 bcrypt 库,绕过 passlib 1.7.4 与 bcrypt 5.x 的不兼容
# (passlib 已停更,其 _load_backend_mixin 在 bcrypt>=4.1 上会抛 ValueError,
#  导致 hash/verify 全部失败)。生成的 hash 格式 $2b$ 与 passlib 一致,向后兼容。
_BCRYPT_MAX_BYTES = 72  # bcrypt 算法的 72 字节明文长度上限


def hash_password(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8")[:_BCRYPT_MAX_BYTES], bcrypt.gensalt()
    ).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain.encode("utf-8")[:_BCRYPT_MAX_BYTES], hashed.encode("utf-8")
        )
    except (ValueError, TypeError):
        return False


def create_access_token(sub: str, expires_minutes: int | None = None) -> str:
    settings = get_settings()
    minutes = expires_minutes if expires_minutes is not None else settings.jwt_expire_minutes
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    payload: dict[str, Any] = {"sub": sub, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise JWTError(f"无法解码 token: {exc}") from exc
