"""数据库类型兼容层。

在 PostgreSQL 环境下使用原生 UUID/JSONB/ARRAY；
在 SQLite 环境下自动降级为 String/JSON。
"""

import uuid

from sqlalchemy import JSON, String, TypeDecorator


class GUID(TypeDecorator):
    """跨数据库 UUID 类型，以 36 字符字符串存储。"""

    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return str(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            if isinstance(value, uuid.UUID):
                return value
            return uuid.UUID(value)
        return value
