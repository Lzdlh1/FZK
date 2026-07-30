"""解析管线:从 ParseJob 出发,完成格式分流 → AI 抽取 → 后处理 → database/formula/manual 填充。

整体为 async;MinIO 取图、格式渲染等同步重活用 ``asyncio.to_thread`` 包裹,避免阻塞事件循环。
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.ai.gateway import AIGateway, AIGatewayError, ExtractionRequest, FieldSpec
from app.models.database_param import DatabaseParam
from app.models.formula import Formula
from app.models.parse_job import ParseJob
from app.models.rule import Rule
from app.models.variable import FewShotRef, Variable, VariablePrompt
from app.services.dag import topological_sort
from app.services.formula.engine import FormulaError, evaluate as evaluate_formula
from app.services.parse import postprocess as pp
from app.services.parse.format import UnsupportedFormatError, format_split
from app.services.storage import get_storage

logger = logging.getLogger(__name__)

# db_vocabulary 仅注入这些"键字段"类目(连接器/端子型号);非键字段(线材长度表等)不注入
KEY_FIELD_CATEGORIES = {"连接器", "端子型号", "connector", "terminal"}


class ParseJobNotFound(Exception):
    pass


# ---------------------------------------------------------------------------
# 数据装载
# ---------------------------------------------------------------------------
def _load_template_variables(db: Session, job: ParseJob):
    """返回 (template, variables list, prompt_map, formula_map)。

    variables 仅 enabled;prompt_map: variable_id -> VariablePrompt;
    formula_map: variable_id -> Formula(仅 formula 型)。
    """
    from app.models.template import Template

    template = db.query(Template).filter(Template.id == job.template_id).first()
    if template is None:
        raise ParseJobNotFound(f"模板 {job.template_id} 不存在")

    variables = (
        db.query(Variable)
        .filter(Variable.template_id == job.template_id, Variable.enabled.is_(True))
        .all()
    )
    var_ids = [v.id for v in variables]
    prompts = (
        db.query(VariablePrompt).filter(VariablePrompt.variable_id.in_(var_ids)).all()
        if var_ids
        else []
    )
    prompt_map = {p.variable_id: p for p in prompts}
    formulas = (
        db.query(Formula).filter(Formula.variable_id.in_(var_ids)).all() if var_ids else []
    )
    formula_map = {f.variable_id: f for f in formulas}
    return template, variables, prompt_map, formula_map


def _build_db_vocabulary(db: Session) -> dict:
    rows = (
        db.query(DatabaseParam)
        .filter(DatabaseParam.enabled.is_(True))
        .all()
    )
    vocab: dict[str, list[str]] = {}
    for r in rows:
        if r.category not in KEY_FIELD_CATEGORIES:
            continue
        vocab.setdefault(r.category, []).append(f"{r.model}:{r.value}")
    return vocab


def _load_rules(db: Session) -> list[str]:
    rows = db.query(Rule).filter(Rule.enabled.is_(True)).all()
    return [r.content for r in rows if r.content]


def _load_few_shot(db: Session, variables: list[Variable]) -> list[dict]:
    """合并所有变量的 few_shot(上限 2 个/模板,按 sort_order)。"""
    var_ids = [v.id for v in variables if v.source_type == "extract"]
    if not var_ids:
        return []
    refs = (
        db.query(FewShotRef)
        .filter(FewShotRef.variable_id.in_(var_ids))
        .order_by(FewShotRef.sort_order.asc())
        .all()
    )
    storage = get_storage()
    out: list[dict] = []
    for ref in refs[:2]:
        try:
            img_bytes, _ = storage.get_bytes(ref.image_oid)
        except Exception as exc:  # noqa: BLE001
            logger.warning("few_shot 图片加载失败 oid=%s: %s", ref.image_oid, exc)
            continue
        out.append({"image": img_bytes, "expected_json": ref.expected_json})
    return out


def _build_field_specs(variables, prompt_map) -> list[FieldSpec]:
    specs: list[FieldSpec] = []
    for v in variables:
        if v.source_type != "extract":
            continue
        prompt = prompt_map.get(v.id)
        oc = (prompt.output_constraints if prompt else None) or {}
        enum = oc.get("enum")
        regex = oc.get("regex")
        specs.append(
            FieldSpec(
                name=v.name,
                description=(prompt.prompt if prompt else v.name),
                data_type=v.data_type,
                unit=v.unit,
                enum=enum,
                regex=regex,
                required=True,
            )
        )
    return specs


# ---------------------------------------------------------------------------
# 后处理
# ---------------------------------------------------------------------------
def _post_process_extract(field_value: dict, variable: Variable, prompt: VariablePrompt | None, text_map: list[dict]) -> dict:
    """对单个 extract 字段结果做后处理,返回规整后的 dict。"""
    pp_cfg = (prompt.post_process if prompt else None) or {}
    confidence_threshold = (prompt.confidence_threshold if prompt else 0.7) or 0.7

    value = field_value.get("value")
    # strip_unit
    if pp_cfg.get("strip_unit") and isinstance(value, str):
        value = pp.strip_unit(value, pp_cfg["strip_unit"])
    # case_normalize
    if pp_cfg.get("case_normalize"):
        value = pp.case_normalize(value, pp_cfg["case_normalize"])
    # db_match
    db_matched = False
    if pp_cfg.get("db_match"):
        matched, _ = pp.db_match(value, pp_cfg["db_match"] if isinstance(pp_cfg.get("db_match"), list) else [])
        if matched is not None:
            db_matched = True

    confidence = pp.normalize_confidence(field_value.get("confidence"))

    # region 融合
    region = field_value.get("source_region")
    if not region:
        region = pp.fuse_region(value, text_map)

    status = field_value.get("status") or "ok"
    if value is None:
        status = "not_found"
    elif confidence < confidence_threshold:
        status = "low_confidence"
    elif db_matched:
        status = "db_matched"

    return {
        "value": value,
        "confidence": confidence,
        "source_region": region,
        "raw_text": field_value.get("raw_text"),
        "unit": variable.unit,
        "alternatives": field_value.get("alternatives") or [],
        "status": status,
    }


def _resolve_database_variable(
    variable: Variable,
    prompt: VariablePrompt | None,
    fields: dict,
    db: Session,
) -> dict:
    """database 型变量:用上游 extract 变量值作查询键查 database_params。"""
    oc = (prompt.output_constraints if prompt else None) or {}
    lookup = oc.get("db_lookup") or {}
    category = lookup.get("category")
    model_var = lookup.get("model_var")
    field_name = lookup.get("field") or variable.name

    model_value = None
    if model_var and model_var in fields:
        mv = fields[model_var].get("value")
        if mv is not None:
            model_value = str(mv).strip()

    if category and model_value:
        row = (
            db.query(DatabaseParam)
            .filter(
                DatabaseParam.enabled.is_(True),
                DatabaseParam.category == category,
                DatabaseParam.model == model_value,
                DatabaseParam.field == field_name,
            )
            .order_by(DatabaseParam.version.desc())
            .first()
        )
        if row is not None:
            return {
                "value": row.value,
                "confidence": 1.0,
                "source_region": None,
                "raw_text": None,
                "unit": row.unit or variable.unit,
                "alternatives": [],
                "status": "db_resolved",
                "db_refs": [{"category": row.category, "model": row.model, "field": row.field, "version": row.version}],
            }
    return {
        "value": None,
        "confidence": 0.0,
        "source_region": None,
        "raw_text": None,
        "unit": variable.unit,
        "alternatives": [],
        "status": "not_found",
        "highlight": True,
    }


def _resolve_formula_variable(
    variable: Variable,
    formula: Formula | None,
    fields: dict,
) -> dict:
    """formula 型变量:用 DAG 已填值求值。"""
    if formula is None:
        return {
            "value": None,
            "confidence": 0.0,
            "source_region": None,
            "raw_text": None,
            "unit": variable.unit,
            "alternatives": [],
            "status": "error",
            "error": "未配置公式",
            "highlight": True,
        }
    values = {}
    for name, fdata in fields.items():
        v = fdata.get("value")
        if v is not None:
            values[name] = v
    try:
        result = evaluate_formula(formula.expression, values)["value"]
    except FormulaError as exc:
        return {
            "value": None,
            "confidence": 0.0,
            "source_region": None,
            "raw_text": None,
            "unit": variable.unit,
            "alternatives": [],
            "status": "error",
            "error": str(exc),
            "substituted_expression": formula.expression,
            "highlight": True,
        }
    return {
        "value": result,
        "confidence": 1.0,
        "source_region": None,
        "raw_text": None,
        "unit": variable.unit,
        "alternatives": [],
        "status": "computed",
        "substituted_expression": formula.expression,
    }


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
async def run_parse_job(db: Session, job_id, gateway: AIGateway) -> dict:
    """执行解析任务,返回 result dict;同时更新 ParseJob.status / result。"""
    job = db.query(ParseJob).filter(ParseJob.id == job_id).first()
    if job is None:
        raise ParseJobNotFound(f"解析任务 {job_id} 不存在")

    try:
        job.status = "parsing"
        db.commit()

        template, variables, prompt_map, formula_map = _load_template_variables(db, job)

        # 2. 取原图
        storage = get_storage()
        drawing_bytes, content_type = await asyncio.to_thread(storage.get_bytes, job.drawing_oid)

        # 3. 格式分流
        split = await asyncio.to_thread(
            format_split, content_type, drawing_bytes, job.drawing_name
        )
        images: list[bytes] = split["images"]
        text_map: list[dict] = split["text_map"]

        # 4. 构建 ExtractionRequest
        field_specs = _build_field_specs(variables, prompt_map)
        db_vocabulary = _build_db_vocabulary(db)
        rules = _load_rules(db)
        few_shot = await asyncio.to_thread(_load_few_shot, db, variables)

        req = ExtractionRequest(
            images=images,
            text_map=text_map,
            fields=field_specs,
            db_vocabulary=db_vocabulary,
            rules=rules,
            few_shot=few_shot,
        )

        # 5. AI 抽取
        resp = await gateway.extract(req)
        ai_fields = resp.fields or {}
        meta = dict(resp.meta or {})
        meta.setdefault("source_kind", split["source_kind"])

        # 6. 后处理 extract 变量
        fields_out: dict[str, dict] = {}
        for v in variables:
            if v.source_type != "extract":
                continue
            raw = ai_fields.get(v.name, {})
            if not isinstance(raw, dict):
                raw = {"value": raw, "confidence": 0.0}
            fields_out[v.name] = _post_process_extract(raw, v, prompt_map.get(v.id), text_map)

        # 7. database 型变量
        for v in variables:
            if v.source_type == "database":
                fields_out[v.name] = _resolve_database_variable(v, prompt_map.get(v.id), fields_out, db)

        # 8. formula 型变量(DAG 拓扑序)
        formula_vars = [v for v in variables if v.source_type == "formula"]
        if formula_vars:
            edges = {}
            for v in formula_vars:
                f = formula_map.get(v.id)
                deps = []
                if f is not None and f.dependencies:
                    # 依赖是 var id;转成对应的 var name(若在 formula_vars 内)
                    id_to_name = {x.id: x.name for x in variables}
                    for dep_id in f.dependencies:
                        if dep_id in id_to_name:
                            deps.append(id_to_name[dep_id])
                edges[v.name] = deps
            # 拓扑序按 name
            order = topological_sort([v.name for v in formula_vars], edges)
            name_to_var = {v.name: v for v in formula_vars}
            for name in order:
                v = name_to_var[name]
                fields_out[v.name] = _resolve_formula_variable(v, formula_map.get(v.id), fields_out)

        # 9. manual 型变量
        for v in variables:
            if v.source_type == "manual":
                fields_out[v.name] = {
                    "value": None,
                    "confidence": 0.0,
                    "source_region": None,
                    "raw_text": None,
                    "unit": v.unit,
                    "alternatives": [],
                    "status": "manual",
                }

        # 10. 组装 result
        db_version = {"max_version": _max_db_version(db)}
        rule_version = {"rule_count": len(rules)}
        result = {
            "fields": fields_out,
            "meta": meta,
            "template_snapshot_ref": {"template_id": str(template.id), "version": template.version},
            "db_version": db_version,
            "rule_version": rule_version,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

        job.result = result
        job.status = "review"
        db.commit()
        return result

    except UnsupportedFormatError as exc:
        _fail_job(db, job, str(exc))
        raise
    except AIGatewayError as exc:
        _fail_job(db, job, f"AI 抽取失败: {exc}")
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("解析任务 %s 失败", job_id)
        _fail_job(db, job, str(exc))
        raise


def _fail_job(db: Session, job: ParseJob, message: str) -> None:
    job.status = "failed"
    result = dict(job.result or {})
    result["error"] = message
    job.result = result
    db.commit()


def _max_db_version(db: Session) -> int:
    rows = db.query(DatabaseParam.version).all()
    return max((r[0] for r in rows), default=0)


# ---------------------------------------------------------------------------
# 单字段重跑
# ---------------------------------------------------------------------------
async def rerun_single_field(
    db: Session,
    job: ParseJob,
    variable: Variable,
    gateway: AIGateway,
) -> dict:
    """整图重跑单个 extract 变量,返回该字段结果。"""
    storage = get_storage()
    drawing_bytes, content_type = await asyncio.to_thread(storage.get_bytes, job.drawing_oid)
    split = await asyncio.to_thread(format_split, content_type, drawing_bytes, job.drawing_name)

    prompt = (
        db.query(VariablePrompt).filter(VariablePrompt.variable_id == variable.id).first()
    )
    field_specs = _build_field_specs([variable], {variable.id: prompt} if prompt else {})
    db_vocabulary = _build_db_vocabulary(db)
    rules = _load_rules(db)
    few_shot = await asyncio.to_thread(_load_few_shot, db, [variable])

    req = ExtractionRequest(
        images=split["images"],
        text_map=split["text_map"],
        fields=field_specs,
        db_vocabulary=db_vocabulary,
        rules=rules,
        few_shot=few_shot,
    )
    resp = await gateway.extract(req)
    raw = resp.fields.get(variable.name, {})
    if not isinstance(raw, dict):
        raw = {"value": raw, "confidence": 0.0}
    return _post_process_extract(raw, variable, prompt, split["text_map"])
