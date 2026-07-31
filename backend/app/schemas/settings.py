"""设置相关 schema：AI 供应商配置、数据库参数。"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ---- AI 供应商 ----

class AIProviderCreate(BaseModel):
    name: str
    endpoint: str
    api_key: str
    model: str
    weight: int = 1
    healthy: bool = True


class AIProviderUpdate(BaseModel):
    name: str | None = None
    endpoint: str | None = None
    api_key: str | None = None
    model: str | None = None
    weight: int | None = None
    healthy: bool | None = None


class AIProviderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    endpoint: str
    model: str
    weight: int = 1
    healthy: bool = True
    last_check_at: datetime | None = None


# ---- 数据库参数 ----

class DatabaseParamCreate(BaseModel):
    category: str
    model: str
    field: str
    value: str
    unit: str | None = None
    enabled: bool = True


class DatabaseParamUpdate(BaseModel):
    category: str | None = None
    model: str | None = None
    field: str | None = None
    value: str | None = None
    unit: str | None = None
    enabled: bool | None = None


class DatabaseParamOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    category: str
    model: str
    field: str
    value: str
    unit: str | None = None
    enabled: bool = True
    version: int = 1


# ---- 健康检查 ----

class AIProviderHealthResult(BaseModel):
    id: UUID
    name: str
    healthy: bool
    error: str | None = None


class AIProviderTestRequest(BaseModel):
    """连通性测试:用未保存的配置直接测试,便于保存前验证(尤其针对中转站)。"""

    name: str | None = None
    endpoint: str
    api_key: str
    model: str


class AIProviderTestResult(BaseModel):
    healthy: bool
    error: str | None = None
    latency_ms: int | None = None
