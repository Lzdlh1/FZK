"""AI 网关路由单测:provider 降级、全部失败、置信度归一。

使用 asyncio.run 在同步测试函数中驱动 async 网关,避免额外 pytest-asyncio 依赖。
"""

import asyncio

import pytest

from app.ai.gateway import (
    AIGateway,
    AIGatewayError,
    ExtractionRequest,
    ExtractionResponse,
    normalize_confidence,
)


class _FakeProvider:
    """最小可注入的 provider mock。"""

    def __init__(self, name, *, raise_exc=None, fields=None, weight=1, healthy=True):
        self.name = name
        self.weight = weight
        self.healthy = healthy
        self._raise_exc = raise_exc
        self._fields = fields or {}
        self.called = 0

    async def extract(self, req: ExtractionRequest) -> ExtractionResponse:
        self.called += 1
        if self._raise_exc is not None:
            raise self._raise_exc
        return ExtractionResponse(fields=self._fields, meta={"model": f"{self.name}-model"})

    async def health(self) -> bool:
        return self.healthy


def _make_req():
    return ExtractionRequest(
        images=[],
        text_map=[],
        fields=[],
        db_vocabulary={},
        rules=[],
        few_shot=[],
    )


def test_gateway_falls_back_to_second_provider():
    p1 = _FakeProvider("p1", raise_exc=RuntimeError("p1 down"))
    p2 = _FakeProvider("p2", fields={"f": {"value": "v", "confidence": 0.8}})
    gw = AIGateway([p1, p2])
    resp = asyncio.run(gw.extract(_make_req()))
    assert resp.fields["f"]["value"] == "v"
    assert p1.called == 1
    assert p2.called == 1
    assert resp.meta["provider"] == "p2"


def test_gateway_all_fail_raises():
    p1 = _FakeProvider("p1", raise_exc=RuntimeError("p1 down"))
    p2 = _FakeProvider("p2", raise_exc=RuntimeError("p2 down"))
    gw = AIGateway([p1, p2])
    with pytest.raises(AIGatewayError):
        asyncio.run(gw.extract(_make_req()))


def test_gateway_prefers_higher_weight_healthy():
    p1 = _FakeProvider("p1", fields={"a": {"value": 1, "confidence": 0.5}}, weight=1)
    p2 = _FakeProvider("p2", fields={"a": {"value": 2, "confidence": 0.5}}, weight=9)
    gw = AIGateway([p1, p2])
    resp = asyncio.run(gw.extract(_make_req()))
    assert resp.meta["provider"] == "p2"
    assert p2.called == 1
    assert p1.called == 0


def test_gateway_skips_unhealthy():
    p1 = _FakeProvider("p1", healthy=False, fields={"a": {"value": 1}})
    p2 = _FakeProvider("p2", fields={"a": {"value": 2, "confidence": 0.5}})
    gw = AIGateway([p1, p2])
    resp = asyncio.run(gw.extract(_make_req()))
    assert resp.meta["provider"] == "p2"
    assert p1.called == 0


def test_gateway_normalizes_none_confidence_without_alternatives():
    p = _FakeProvider("p", fields={"f": {"value": "v", "confidence": None}})
    gw = AIGateway([p])
    resp = asyncio.run(gw.extract(_make_req()))
    assert resp.fields["f"]["confidence"] == 0.5


def test_normalize_confidence_variants():
    assert normalize_confidence(None) == 0.5
    assert normalize_confidence(None, alternatives=None) == 0.5
    assert normalize_confidence(1.5) == 1.0
    assert normalize_confidence(-0.3) == 0.0
    assert normalize_confidence(0.7) == 0.7
    assert normalize_confidence(
        None,
        alternatives=[{"value": "a", "confidence": 0.9}, {"value": "b", "confidence": 0.4}],
    ) == pytest.approx(0.5)
