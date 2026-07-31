"""解析任务 API:创建/列表/详情/运行/单字段重跑/审核/原图下载。"""

from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.ai.gateway import AIGatewayError, make_default_gateway
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.parse_job import HistorySnapshot, ParseJob
from app.models.template import Template
from app.models.user import User
from app.models.variable import Variable
from app.schemas.parse_job import (
    FieldResult,
    HistorySnapshotOut,
    OutputRequest,
    OutputResponse,
    ParseJobListItem,
    ParseJobOut,
    ParseJobResult,
    ReviewRequest,
    RerunFieldRequest,
)
from app.schemas.template import TemplateOut, VariableOut
from app.services.output.archive import create_history_snapshot
from app.services.output.generator import (
    build_output_filename,
    fill_snapshot_with_values,
    snapshot_to_xlsx_bytes,
)
from app.services.parse.pipeline import (
    ParseJobNotFound,
    rerun_single_field,
    run_parse_job,
)
from app.services.storage import _sanitize_name, get_storage, make_oid, make_storage_path
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
    name = drawing_name or drawing.filename or "drawing"
    # 按图纸名建子目录,附加短 uuid 保证唯一;原图用原始文件名,便于查找。
    subfolder = f"{_sanitize_name(name)}_{uuid.uuid4().hex[:8]}"
    drawing_oid = make_storage_path(subfolder, drawing.filename, content_type)

    storage = get_storage()
    try:
        await asyncio.to_thread(storage.upload_bytes, drawing_oid, data, content_type)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"对象存储写入失败: {exc}")

    job = ParseJob(template_id=tid, drawing_oid=drawing_oid, drawing_name=name, status="pending")
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


@router.delete("/parse-jobs/{job_id}")
def delete_parse_job(
    job_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """删除解析任务:连同历史快照及对象存储中的原图/输出文件一起清理。"""
    job = _get_job_or_404(db, job_id)
    storage = get_storage()

    # 收集需要删除的对象:原图 + 各快照的输出文件
    oids_to_delete: list[str] = []
    if job.drawing_oid:
        oids_to_delete.append(job.drawing_oid)
    snapshots = (
        db.query(HistorySnapshot)
        .filter(HistorySnapshot.parse_job_id == job.id)
        .all()
    )
    for snap in snapshots:
        if snap.output_oid:
            oids_to_delete.append(snap.output_oid)

    # 删除 DB 记录(快照 + 任务)
    db.query(HistorySnapshot).filter(HistorySnapshot.parse_job_id == job.id).delete()
    db.delete(job)
    db.commit()

    # 删除存储对象(尽力删除,失败不阻断)
    for oid in oids_to_delete:
        try:
            storage.delete_object(oid)
        except Exception as exc:  # noqa: BLE001
            logger.warning("删除对象 %s 失败: %s", oid, exc)

    return {"ok": True}


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


_XLSX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


def _latest_snapshot(db: Session, job_id: uuid.UUID) -> HistorySnapshot | None:
    return (
        db.query(HistorySnapshot)
        .filter(HistorySnapshot.parse_job_id == job_id)
        .order_by(HistorySnapshot.created_at.desc())
        .first()
    )


@router.post("/parse-jobs/{job_id}/output", response_model=OutputResponse)
async def generate_output(
    job_id: str,
    payload: OutputRequest | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """生成最终 Excel,归档快照,job.status -> done。"""
    job = _get_job_or_404(db, job_id)
    if job.status != "review" or not job.result:
        raise HTTPException(
            status_code=400, detail="任务不在审核状态或无解析结果,无法输出"
        )

    template = db.query(Template).filter(Template.id == job.template_id).first()
    if template is None:
        raise HTTPException(status_code=404, detail="模板不存在")

    variables = load_variables_with_relations(db, job.template_id)
    fields = (job.result or {}).get("fields") or {}

    filled = fill_snapshot_with_values(template.univer_snapshot or {}, variables, fields)
    xlsx_bytes = snapshot_to_xlsx_bytes(filled)

    custom_name = payload.filename if payload else None
    filename = build_output_filename(job.drawing_name, custom_name)
    # 输出辅助卡存到与原图相同的子目录下,便于一起查找。
    # drawing_oid 形如 "<subfolder>/<file>";取其父目录作为输出子目录。
    subfolder = str(Path(job.drawing_oid).parent) if job.drawing_oid else _sanitize_name(job.drawing_name)
    oid = make_storage_path(subfolder, filename, _XLSX_MEDIA_TYPE)

    storage = get_storage()
    try:
        await asyncio.to_thread(storage.upload_bytes, oid, xlsx_bytes, _XLSX_MEDIA_TYPE)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"输出文件存储失败: {exc}")

    snapshot = create_history_snapshot(db, job, template, oid)
    job.status = "done"
    db.commit()
    db.refresh(snapshot)

    return OutputResponse(
        output_url=f"/api/parse-jobs/{job_id}/output",
        snapshot_id=str(snapshot.id),
        filename=filename,
    )


@router.get("/parse-jobs/{job_id}/output")
def get_output(
    job_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """下载已生成的 Excel 二进制流;未输出则 404。"""
    job = _get_job_or_404(db, job_id)
    snapshot = _latest_snapshot(db, job.id)
    if snapshot is None or not snapshot.output_oid:
        raise HTTPException(status_code=404, detail="尚未生成输出文件")
    storage = get_storage()
    try:
        data, _ = storage.get_bytes(snapshot.output_oid)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=404, detail=f"输出文件获取失败: {exc}")
    return Response(
        content=data,
        media_type=_XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="output.xlsx"'},
    )


@router.get("/parse-jobs/{job_id}/history", response_model=HistorySnapshotOut)
def get_history(
    job_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """按 parse_job_id 查最近一条 HistorySnapshot;无则 404。"""
    job = _get_job_or_404(db, job_id)
    snapshot = _latest_snapshot(db, job.id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="无历史快照")
    return HistorySnapshotOut(
        id=str(snapshot.id),
        parse_job_id=str(snapshot.parse_job_id),
        drawing_oid=snapshot.drawing_oid,
        template_snapshot=snapshot.template_snapshot,
        db_version=snapshot.db_version,
        rule_version=snapshot.rule_version,
        ai_raw_result=snapshot.ai_raw_result,
        manual_edits=snapshot.manual_edits,
        output_oid=snapshot.output_oid,
        created_at=snapshot.created_at,
    )
