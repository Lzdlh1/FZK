"""快照归档:每次输出创建一条 HistorySnapshot,形成可追溯链。"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.parse_job import HistorySnapshot, ParseJob
from app.models.template import Template


def create_history_snapshot(
    db: Session, job: ParseJob, template: Template, output_oid: str
) -> HistorySnapshot:
    """组装并插入一条 HistorySnapshot(不 commit,由调用方提交)。

    - template_snapshot: 当时的模板 univer_snapshot;
    - db_version / rule_version: 优先取 result 中管线写入的,缺失则记 MVP 简化信息;
    - ai_raw_result: 整个审核后 result(含 fields + meta);
    - manual_edits: result.manual_edits(review 接口写入);
    - output_oid: 生成的 xlsx 对象 oid。
    """
    result = job.result or {}
    now_iso = datetime.now(timezone.utc).isoformat()
    db_version = result.get("db_version") or {
        "generated_at": now_iso,
        "note": "mvp snapshot",
    }
    rule_version = result.get("rule_version") or {
        "generated_at": now_iso,
        "note": "mvp snapshot",
    }

    snapshot = HistorySnapshot(
        parse_job_id=job.id,
        drawing_oid=job.drawing_oid,
        template_snapshot=template.univer_snapshot or {},
        db_version=db_version,
        rule_version=rule_version,
        ai_raw_result=result,
        manual_edits=result.get("manual_edits") or {},
        output_oid=output_oid,
    )
    db.add(snapshot)
    db.flush()  # 填充 snapshot.id,供调用方返回
    return snapshot
