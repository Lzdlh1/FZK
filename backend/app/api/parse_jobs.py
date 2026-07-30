"""解析任务 API:创建/列表/详情/运行/单字段重跑/审核/原图下载。"""

from __future__ import annotations

import asyncio
import logging
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.ai.gateway import AIGatewayError, make_default_gateway
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.parse_job import ParseJob
from app.models.template import Template
from app.models.user import User
from app.models.variable import Variable
from app.schemas.parse_job import (
    FieldResult,
    ParseJobListItem,
    ParseJobOut,
    ParseJobResult,
    ReviewRequest,
    RerunFieldRequest,
)
from app.schemas.template import TemplateOut, VariableOut
from app.services.parse.pipeline import (
    ParseJobNotFound,
    rerun_single_field,
    run_parse_job,
)
from app.services.storage import get_storage, make_oid
from app.services.template_loader import load_variables_with_relations, variable_to_out

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# 序列化辅助
# ---------------------------------------------------------------------------
def _variable_out(v: Variable) -> VariableOut:
    # 接收已通过 load_variables_with_relations 挂载 prompt/formula 的变量
    return variable_to_out(v)


def _template_out(db: Session, job: ParseJob) -> TemplateOut | None:
    template = db.query(Template).filter(Template.id == job.template_id).first()
    if template is None:
        return None
    variables = load_variables_with_relations(db, template.id)
    return TemplateOut(
        id=template.id,
        name=template.name,
        version=template.version,
        updated_at=template.updated_at,
        owner_id=template.owner_id,
        variables=[_variable_out(v) for v in variables],
    )


def _result_out(result: dict | None) -> ParseJobResult | None:
    if result is None:
        return None
    fields = {}
    for name, fdata in (result.get("fields") or {}).items():
        if not isinstance(fdata, dict):
            fields[name] = FieldResult(value=fdata)
        else:
            fields[name] = FieldResult(**fdata)
    return ParseJobResult(
        fields=fields,
        meta=result.get("meta") or {},
        error=result.get("error"),
        template_snapshot_ref=result.get("template_snapshot_ref"),
        db_version=result.get("db_version"),
        rule_version=result.get("rule_version"),
        completed_at=result.get("completed_at"),
    )


def _job_out(db: Session, job: ParseJob, include_template: bool = False) -> ParseJobOut:
    return ParseJobOut(
        id=str(job.id),
        template_id=str(job.template_id),
        drawing_name=job.drawing_name,
        status=job.status,
        result=_result_out(job.result),
        created_at=job.created_at,
        template=_template_out(db, job) if include_template else None,
    )


# ---------------------------------------------------------------------------
# 路由
# ---------------------------------------------------------------------------
@router.post("/parse-jobs", response_model=ParseJobOut, status_code=status.HTTP_201_CREATED)
async def create_parse_job(
    template_id: str = Form(...),
    drawing: UploadFile = File(...),
    drawing_name: str | None = Form(None),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    try:
        tid = uuid.UUID(template_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="template_id 不是合法 UUID")
    template = db.query(Template).filter(Template.id == tid).first()
    if template is None:
        raise HTTPException(status_code=404, detail="模板不存在")

    data = await drawing.read()
    if not data:
        raise HTTPException(status_code=400, detail="上传文件为空")
    content_type = drawing.content_type or "application/octet-stream"
    oid = make_oid(drawing.filename, content_type)
    name = drawing_name or drawing.filename or oid

    storage = get_storage()
    try:
        await asyncio.to_thread(storage.upload_bytes, oid, data, content_type)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"对象存储写入失败: {exc}")

    job = ParseJob(template_id=tid, drawing_oid=oid, drawing_name=name, status="pending")
    db.add(job)
    db.commit()
    db.refresh(job)
    return _job_out(db, job, include_template=False)


@router.get("/parse-jobs", response_model=list[ParseJobListItem])
def list_parse_jobs(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    jobs = (
        db.query(ParseJob)
        .join(Template, ParseJob.template_id == Template.id)
        .filter(Template.owner_id == user.id)
        .order_by(ParseJob.created_at.desc())
        .all()
    )
    return [
        ParseJobListItem(
            id=str(j.id),
            template_id=str(j.template_id),
            drawing_name=j.drawing_name,
            status=j.status,
            created_at=j.created_at,
        )
        for j in jobs
    ]


def _get_job_or_404(db: Session, job_id: str) -> ParseJob:
    try:
        jid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="id 不是合法 UUID")
    job = db.query(ParseJob).filter(ParseJob.id == jid).first()
    if job is None:
        raise HTTPException(status_code=404, detail="解析任务不存在")
    return job


@router.get("/parse-jobs/{job_id}", response_model=ParseJobOut)
def get_parse_job(
    job_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    job = _get_job_or_404(db, job_id)
    return _job_out(db, job, include_template=True)


@router.post("/parse-jobs/{job_id}/run", response_model=ParseJobOut)
async def run_parse_job_endpoint(
    job_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    job = _get_job_or_404(db, job_id)
    gateway = make_default_gateway(db)
    if gateway is None:
        raise HTTPException(status_code=400, detail="未配置 AI provider,请先在系统设置添加")
    try:
        await run_parse_job(db, job.id, gateway)
    except ParseJobNotFound:
        raise HTTPException(status_code=404, detail="解析任务或模板不存在")
    except (AIGatewayError, Exception) as exc:  # noqa: BLE001
        # 管线已将 job 标记为 failed 并写入 result.error;返回更新后的任务
        logger.warning("解析任务 %s 执行失败: %s", job_id, exc)
    db.refresh(job)
    return _job_out(db, job, include_template=False)


@router.post("/parse-jobs/{job_id}/rerun-field")
async def rerun_field_endpoint(
    job_id: str,
    payload: RerunFieldRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    job = _get_job_or_404(db, job_id)
    gateway = make_default_gateway(db)
    if gateway is None:
        raise HTTPException(status_code=400, detail="未配置 AI provider,请先在系统设置添加")
    try:
        vid = uuid.UUID(payload.variable_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="variable_id 不是合法 UUID")
    variable = (
        db.query(Variable)
        .filter(Variable.id == vid, Variable.template_id == job.template_id)
        .first()
    )
    if variable is None:
        raise HTTPException(status_code=404, detail="变量不存在或不属于该任务模板")
    if variable.source_type != "extract":
        raise HTTPException(status_code=400, detail="仅 extract 型变量支持单字段重跑")
    try:
        field = await rerun_single_field(db, job, variable, gateway)
    except (AIGatewayError, Exception) as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"单字段重跑失败: {exc}")
    return {"field": field}


@router.put("/parse-jobs/{job_id}/review", response_model=ParseJobOut)
def review_parse_job(
    job_id: str,
    payload: ReviewRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    job = _get_job_or_404(db, job_id)
    if not job.result:
        raise HTTPException(status_code=400, detail="任务尚无解析结果,无法审核")
    result = dict(job.result)
    fields = dict(result.get("fields") or {})
    overrides = set(payload.manual_overrides)

    for name, value in (payload.edits or {}).items():
        fdata = fields.get(name)
        if not isinstance(fdata, dict):
            fdata = {}
        fdata["value"] = value
        fdata["confidence"] = 1.0
        if name in overrides:
            fdata["status"] = "manual"
        elif fdata.get("status") in (None, "not_found"):
            fdata["status"] = "ok"
        fields[name] = fdata

    result["fields"] = fields
    result["manual_edits"] = {
        "edits": payload.edits or {},
        "manual_overrides": payload.manual_overrides or [],
    }
    job.result = result
    db.commit()
    db.refresh(job)
    return _job_out(db, job, include_template=False)


@router.get("/parse-jobs/{job_id}/drawing")
def get_drawing(
    job_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    job = _get_job_or_404(db, job_id)
    storage = get_storage()
    try:
        data, content_type = storage.get_bytes(job.drawing_oid)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=404, detail=f"原图获取失败: {exc}")
    return Response(content=data, media_type=content_type)
