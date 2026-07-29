from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class FieldSpec:
    name: str
    description: str
    data_type: str
    unit: str | None = None
    enum: list[str] | None = None
    regex: str | None = None
    required: bool = True


@dataclass
class ExtractionRequest:
    images: list[bytes]
    text_map: list[dict]
    fields: list[FieldSpec]
    db_vocabulary: dict
    rules: list[str]
    few_shot: list[dict]


@dataclass
class ExtractionResponse:
    fields: dict
    meta: dict


class AIProvider(Protocol):
    name: str

    async def extract(self, req: ExtractionRequest) -> ExtractionResponse: ...

    async def health(self) -> bool: ...


class AIGateway:
    """AI 网关:按 weight + healthy 路由 provider,对置信度归一,全部失败时抛错。"""

    def __init__(self, providers: list[AIProvider]):
        self.providers = providers

    async def extract(self, req: ExtractionRequest) -> ExtractionResponse:
        # 路由策略:优先选择 healthy 且 weight 较高的 provider;
        # 对返回字段做置信度归一;所有 provider 均失败时抛错。
        raise NotImplementedError

    async def run_health_checks(self) -> None:
        # 遍历所有 provider 调用 health(),更新 healthy / last_check_at。
        raise NotImplementedError
