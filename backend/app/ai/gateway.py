from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
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
    healthy: bool

    async def extract(self, req: ExtractionRequest) -> ExtractionResponse: ...

    async def health(self) -> bool: ...


class AIGatewayError(Exception):
    """所有 AI provider 不可用或返回不可恢复错误。"""


def normalize_confidence(confidence, alternatives=None) -> float:
    """置信度归一。

    - 已在 [0,1] 原样返回;
    - >1 或 <0 clip 到边界;
    - None 时按 alternatives top1 领先度估算(top1 - top2);无 alternatives 给 0.5。
    """
    if confidence is None:
        if alternatives:
            scores = []
            for alt in alternatives:
                if isinstance(alt, dict):
                    s = alt.get("confidence") or alt.get("score")
                    if s is not None:
                        try:
                            scores.append(float(s))
                        except (TypeError, ValueError):
                            pass
                else:
                    try:
                        scores.append(float(alt))
                    except (TypeError, ValueError):
                        pass
            if len(scores) >= 2:
                top1 = max(scores)
                scores_sorted = sorted(scores, reverse=True)
                top2 = scores_sorted[1]
                return float(max(0.0, min(1.0, top1 - top2)))
            if len(scores) == 1:
                # 仅一个候选,无法估算领先度
                return 0.5
        return 0.5
    try:
        c = float(confidence)
    except (TypeError, ValueError):
        return 0.5
    if c > 1.0:
        return 1.0
    if c < 0.0:
        return 0.0
    return c


class AIGateway:
    """AI 网关:按 (healthy DESC, weight DESC) 路由 provider,对置信度归一。

    全部 provider 失败时抛 AIGatewayError。
    """

    def __init__(self, providers: list[AIProvider], db_session_factory=None):
        self.providers = list(providers)
        self.db_session_factory = db_session_factory

    def _ordered_providers(self) -> list[AIProvider]:
        # weight 通过 getattr 取,Protocol 只要求 name/healthy/extract/health
        def sort_key(p: AIProvider):
            healthy = 1 if getattr(p, "healthy", True) else 0
            weight = getattr(p, "weight", 1)
            return (healthy, weight)

        return sorted(self.providers, key=sort_key, reverse=True)

    async def extract(self, req: ExtractionRequest) -> ExtractionResponse:
        errors: list[str] = []
        for provider in self._ordered_providers():
            if not getattr(provider, "healthy", True):
                continue
            try:
                resp = await provider.extract(req)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{provider.name}: {exc}")
                continue
            # 置信度归一
            for fname, fdata in (resp.fields or {}).items():
                if isinstance(fdata, dict):
                    alts = fdata.get("alternatives")
                    fdata["confidence"] = normalize_confidence(fdata.get("confidence"), alts)
            # 记录实际使用的 provider 名(若 provider 未填则补)
            meta = resp.meta or {}
            meta.setdefault("provider", provider.name)
            resp.meta = meta
            return resp
        raise AIGatewayError("所有 AI provider 不可用;详情: " + " | ".join(errors) if errors else "所有 AI provider 不可用")

    async def run_health_checks(self) -> None:
        for provider in self.providers:
            try:
                ok = await provider.health()
            except Exception:  # noqa: BLE001
                ok = False
            try:
                provider.healthy = bool(ok)
            except AttributeError:
                pass
            try:
                provider.last_check = datetime.now(timezone.utc)
            except AttributeError:
                pass


def make_default_gateway(db) -> "AIGateway | None":
    """从 ai_providers 表读 enabled 配置,实例化已知 provider 适配器。

    无任何配置时返回 None(调用方决定降级为纯手动)。

    注意:api_key_enc 字段在 MVP 中以明文存储,TODO 后续加密。
    """
    from app.models.ai_provider import AIProvider as AIProviderModel
    from app.ai.providers.openai_compatible import OpenAICompatibleProvider

    rows = (
        db.query(AIProviderModel)
        .filter(AIProviderModel.healthy.is_(True))
        .order_by(AIProviderModel.weight.desc())
        .all()
    )
    if not rows:
        return None
    providers: list[AIProvider] = []
    for row in rows:
        providers.append(
            OpenAICompatibleProvider(
                name=row.name,
                endpoint=row.endpoint,
                api_key=row.api_key_enc,  # TODO 加密
                model=row.model,
                weight=row.weight,
            )
        )
    return AIGateway(providers)
