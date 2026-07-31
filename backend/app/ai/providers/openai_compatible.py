"""OpenAI 兼容视觉模型 provider。

适配所有遵循 OpenAI Chat Completions 多模态协议的端点(OpenAI 官方、各类兼容网关)。
"""

from __future__ import annotations

import base64
import io
import json
import time
from datetime import datetime, timezone

import httpx

from app.ai.gateway import ExtractionRequest, ExtractionResponse


def _bytes_to_jpeg(data: bytes) -> bytes:
    """把任意图片字节统一转 JPEG(PDF 渲染出的 PNG 也走这里)。"""
    from PIL import Image

    img = Image.open(io.BytesIO(data))
    if img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGB")
    elif img.mode != "RGB":
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def _bytes_to_data_url(data: bytes) -> str:
    jpeg = _bytes_to_jpeg(data)
    b64 = base64.b64encode(jpeg).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"


class OpenAICompatibleProvider:
    """OpenAI 兼容端点的 provider 实现。"""

    def __init__(self, name: str, endpoint: str, api_key: str, model: str, weight: int = 1):
        self.name = name
        self.endpoint = endpoint
        self.api_key = api_key
        self.model = model
        self.weight = weight
        self.healthy: bool = True
        self.last_check: datetime | None = None

    # ---- prompt 构造(B 设计)----
    def _build_system_prompt(self, req: ExtractionRequest) -> str:
        lines = [
            "你是一个工程图纸/文档信息抽取助手。根据用户提供的图片和文字地图,精确抽取指定字段。",
            "严格只输出一个 JSON 对象,不要任何额外解释、markdown 代码块或前后缀。",
            "JSON schema:{\"fields\": {\"<字段名>\": {\"value\": <值>, \"confidence\": 0.0-1.0, \"raw_text\": \"原始文本\", \"source_region\": {\"page\": 1, \"bbox\": [x,y,w,h]} | null, \"alternatives\": [{\"value\": ..., \"confidence\": ...}]}}}",
            "要求:",
            "- value 用与字段 data_type 匹配的类型(string/number/integer/enum);无法确定时为 null。",
            "- confidence 为 [0,1] 浮点,反映你对该字段值的把握。",
            "- source_region.bbox 归一化到 [0,1];若来自文字地图则复用其 bbox;无法定位时为 null。",
            "- alternatives 给出候选值及其置信度(可空)。",
            "- 找不到的字段:value=null, confidence=0.0。",
        ]
        if req.rules:
            lines.append("业务规则:")
            for r in req.rules:
                lines.append(f"- {r}")
        return "\n".join(lines)

    def _build_fields_text(self, req: ExtractionRequest) -> str:
        lines = ["需要抽取的字段:"]
        for f in req.fields:
            parts = [f"- {f.name} (data_type={f.data_type}", f"description={f.description}"]
            if f.unit:
                parts.append(f"unit={f.unit}")
            if f.enum:
                parts.append(f"enum={f.enum}")
            if f.regex:
                parts.append(f"regex={f.regex}")
            parts.append(f"required={f.required}")
            lines.append(" ".join(parts) + ")")
        return "\n".join(lines)

    def _build_text_map_text(self, req: ExtractionRequest) -> str:
        if not req.text_map:
            return "文字地图:(无)"
        lines = ["文字地图(已按页面归一化 bbox):"]
        for i, item in enumerate(req.text_map):
            text = item.get("text", "")
            bbox = item.get("bbox")
            page = item.get("page", 1)
            lines.append(f"[{i}] page={page} bbox={bbox} text={text!r}")
        return "\n".join(lines)

    def _build_db_vocabulary_text(self, req: ExtractionRequest) -> str:
        if not req.db_vocabulary:
            return "DB 候选词表:(无)"
        lines = ["DB 候选词表(优先从这些候选中选择/校验):"]
        for category, cands in req.db_vocabulary.items():
            lines.append(f"- {category}: {cands}")
        return "\n".join(lines)

    def _build_messages(self, req: ExtractionRequest) -> list[dict]:
        system = self._build_system_prompt(req)
        user_content: list[dict] = []

        # few-shot 的图作为前置 image_url 注入
        for fs in req.few_shot:
            fs_image = fs.get("image")
            if fs_image:
                user_content.append(
                    {"type": "image_url", "image_url": {"url": _bytes_to_data_url(fs_image)}}
                )
            expected = fs.get("expected_json")
            if expected is not None:
                user_content.append(
                    {
                        "type": "text",
                        "text": f"(示例:该图期望输出 JSON 为 {json.dumps(expected, ensure_ascii=False)})",
                    }
                )

        # 主图
        for img in req.images:
            user_content.append({"type": "image_url", "image_url": {"url": _bytes_to_data_url(img)}})

        user_content.append({"type": "text", "text": self._build_fields_text(req)})
        user_content.append({"type": "text", "text": self._build_text_map_text(req)})
        user_content.append({"type": "text", "text": self._build_db_vocabulary_text(req)})
        user_content.append(
            {"type": "text", "text": "请仅输出符合 schema 的 JSON 对象。"}
        )

        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ]

    def _parse_content_json(self, content: str) -> dict:
        """从模型返回文本中提取 JSON(兼容带代码块/前后缀的情况)。"""
        text = content.strip()
        if text.startswith("```"):
            # 去掉 ```json ... ``` 包裹
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
            text = text.strip()
        # 尝试找到第一个 { 到最后一个 }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start : end + 1]
        return json.loads(text)

    async def extract(self, req: ExtractionRequest) -> ExtractionResponse:
        messages = self._build_messages(req)
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        start = time.perf_counter()
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(self.endpoint, json=payload, headers=headers)
        latency_ms = int((time.perf_counter() - start) * 1000)
        if resp.status_code >= 400:
            raise RuntimeError(f"OpenAI 兼容端点返回 {resp.status_code}: {resp.text[:300]}")
        data = resp.json()

        content = ""
        choices = data.get("choices") or []
        if choices:
            msg = choices[0].get("message") or {}
            content = msg.get("content") or ""
        try:
            parsed = self._parse_content_json(content)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"模型返回非 JSON:{content[:300]}") from exc

        fields = parsed.get("fields") if isinstance(parsed, dict) else None
        if not isinstance(fields, dict):
            fields = {}

        # schema 校验:每 field 至少 value+confidence;缺失补默认
        for fname, fdata in list(fields.items()):
            if not isinstance(fdata, dict):
                fields[fname] = {"value": fdata, "confidence": 0.0, "status": "ok"}
                continue
            fdata.setdefault("value", None)
            fdata.setdefault("confidence", 0.0)
            fdata.setdefault("raw_text", None)
            fdata.setdefault("source_region", None)
            fdata.setdefault("alternatives", [])
            fdata.setdefault("status", "ok")
        # 缺失字段补 not_found
        for spec in req.fields:
            if spec.name not in fields:
                fields[spec.name] = {
                    "value": None,
                    "confidence": 0.0,
                    "raw_text": None,
                    "source_region": None,
                    "alternatives": [],
                    "status": "not_found",
                }

        usage = data.get("usage") or {}
        meta = {
            "provider": self.name,
            "model": self.model,
            "tokens_in": usage.get("prompt_tokens"),
            "tokens_out": usage.get("completion_tokens"),
            "latency_ms": latency_ms,
        }
        return ExtractionResponse(fields=fields, meta=meta)

    async def health(self) -> bool:
        """连通性检查:发送一个最小 chat completion 请求。

        之所以不用 GET /models:很多中转站/网关不支持 /models 接口,
        但 chat completions 能正常工作。真实发一条 "ping" 消息更可靠。
        """
        try:
            return await self.test_connection()
        except Exception:  # noqa: BLE001
            self.healthy = False
            return False

    async def test_connection(self) -> bool:
        """发送最小 chat completion 请求验证端点+key+model 可用。

        成功(2xx 且有 choices)返回 True,否则抛出带状态码/响应体的 RuntimeError。
        供「测试连通性」按钮使用,错误信息会回显给用户。
        """
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 1,
            "temperature": 0,
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(self.endpoint, json=payload, headers=headers)
        if resp.status_code >= 400:
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
        data = resp.json()
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError(f"响应中无 choices: {str(data)[:200]}")
        self.healthy = True
        self.last_check = datetime.now(timezone.utc)
        return True
