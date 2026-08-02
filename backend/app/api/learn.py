"""AI 学习 API:对话式训练。

- POST /learn/try          上传示例图纸 + 选择模板 → AI 尝试解析(不创建解析任务)
- POST /learn/samples      把纠正后的结果保存为该模板的训练样本(LearnSample)
- GET  /learn/samples      查看某模板已训练的样本列表
- DELETE /learn/samples/{id} 删除样本(连同存储中的图纸)
- GET  /learn/samples/{id}/image 预览样本图纸

训练样本在解析该模板时由管线注入(few-shot),逐步纠正 AI 的抽取逻辑。
"""

from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.ai.gateway import AIGatewayError, ExtractionRequest, make_default_gateway
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.learn_sample import LearnSample
from app.models.template import Template
from app.models.user import User
from app.models.variable import Variable, VariablePrompt
from app.schemas.learn import LearnSampleCreate, LearnSampleOut, LearnTryResponse
from app.services.parse.format import format_split
from app.services.parse.pipeline import (
    _build_db_vocabulary,
    _build_field_specs,
    _load_learn_samples,
    _load_rules,
    _post_process_extract,
)
from app.services.storage import _sanitize_name, get_storage, make_storage_path

router = APIRouter()


def _get_owned_template_or_404(db: Session, template_id: uuid.UUID, user: User) -> Template:
    template = (
        db.query(Template)
        .filter(Template.id == template_id, Template.owner_id == user.id)
        .first()
    )
    if template is None:
        raise HTTPException(status_code=404, detail="模板不存在")
    return template


# ---------------------------------------------------------------------------
# 尝试解析
# ---------------------------------------------------------------------------
@router.post("/try", response_model=LearnTryResponse)
async def learn_try(
    template_id: str = Form(...),
    drawing: UploadFile = File(...),
    drawing_name: str | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        tid = uuid.UUID(template_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="template_id 不是合法 UUID")
    template = _get_owned_template_or_404(db, tid, user)

    data = await drawing.read()
    if not data:
        raise HTTPException(status_code=400, detail="上传文件为空")
    content_type = drawing.content_type or "application/octet-stream"
    name = drawing_name or drawing.filename or "learn-example"

    # 仅 extract 型变量参与 AI 抽取
    variables = (
        db.query(Variable)
        .filter(
            Variable.template_id == tid,
            Variable.enabled.is_(True),
            Variable.source_type == "extract",
        )
        .all()
    )
    if not variables:
        raise HTTPException(
            status_code=400,
            detail="该模板未定义可抽取变量,请先在模板设计器添加",
        )

    prompts = (
        db.query(VariablePrompt)
        .filter(VariablePrompt.variable_id.in_([v.id for v in variables]))
        .all()
    )
    prompt_map = {p.variable_id: p for p in prompts}

    # 示例图纸存到对象存储(按图纸名分目录),供保存样本时引用
    storage = get_storage()
    subfolder = f"{_sanitize_name(name)}_{uuid.uuid4().hex[:8]}"
    image_oid = make_storage_path(subfolder, drawing.filename, content_type)
    try:
        await asyncio.to_thread(storage.upload_bytes, image_oid, data, content_type)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"对象存储写入失败: {exc}")

    # 格式分流
    try:
        split = await asyncio.to_thread(format_split, content_type, data, name)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"图纸格式不支持: {exc}")

    gateway = make_default_gateway(db)
    if gateway is None:
        raise HTTPException(status_code=400, detail="未配置 AI provider,请先在系统设置添加")

    field_specs = _build_field_specs(variables, prompt_map)
    db_vocabulary = _build_db_vocabulary(db)
    rules = _load_rules(db)
    few_shot = await asyncio.to_thread(_load_learn_samples, db, tid)

    req = ExtractionRequest(
        images=split["images"],
        text_map=split["text_map"],
        fields=field_specs,
        db_vocabulary=db_vocabulary,
        rules=rules,
        few_shot=few_shot,
    )
    try:
        resp = await gateway.extract(req)
    except AIGatewayError as exc:
        raise HTTPException(status_code=502, detail=f"AI 抽取失败: {exc}")

    ai_fields = resp.fields or {}
    fields_out: dict = {}
    for v in variables:
        raw = ai_fields.get(v.name, {})
        if not isinstance(raw, dict):
            raw = {"value": raw, "confidence": 0.0}
        fields_out[v.name] = _post_process_extract(raw, v, prompt_map.get(v.id), split["text_map"])

    return LearnTryResponse(
        image_oid=image_oid,
        drawing_name=name,
        fields=fields_out,
        meta=dict(resp.meta or {}),
    )


# ---------------------------------------------------------------------------
# 训练样本 CRUD
# ---------------------------------------------------------------------------
@router.post("/samples", response_model=LearnSampleOut, status_code=status.HTTP_201_CREATED)
def create_sample(
    body: LearnSampleCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _get_owned_template_or_404(db, body.template_id, user)
    if not body.expected_json:
        raise HTTPException(status_code=400, detail="期望结果不能为空")

    max_sort = (
        db.query(func.max(LearnSample.sort_order))
        .filter(LearnSample.template_id == body.template_id)
        .scalar()
        or 0
    )
    row = LearnSample(
        template_id=body.template_id,
        image_oid=body.image_oid,
        expected_json=body.expected_json,
        sort_order=max_sort + 1,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/samples", response_model=list[LearnSampleOut])
def list_samples(
    template_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _get_owned_template_or_404(db, template_id, user)
    return (
        db.query(LearnSample)
        .filter(LearnSample.template_id == template_id)
        .order_by(LearnSample.sort_order.desc(), LearnSample.created_at.desc())
        .all()
    )


@router.delete("/samples/{sample_id}")
def delete_sample(
    sample_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = (
        db.query(LearnSample)
        .join(Template, LearnSample.template_id == Template.id)
        .filter(LearnSample.id == sample_id, Template.owner_id == user.id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="样本不存在")
    oid = row.image_oid
    db.delete(row)
    db.commit()
    try:
        get_storage().delete_object(oid)
    except Exception:  # noqa: BLE001
        pass
    return {"ok": True}


@router.get("/samples/{sample_id}/image")
def get_sample_image(
    sample_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = (
        db.query(LearnSample)
        .join(Template, LearnSample.template_id == Template.id)
        .filter(LearnSample.id == sample_id, Template.owner_id == user.id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="样本不存在")
    try:
        data, content_type = get_storage().get_bytes(row.image_oid)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=404, detail=f"样本图纸获取失败: {exc}")
    return Response(content=data, media_type=content_type)
