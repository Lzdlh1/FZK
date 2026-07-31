import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.db.types import GUID


class ParseJob(Base):
    __tablename__ = "parse_jobs"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("templates.id"))
    drawing_oid: Mapped[str] = mapped_column(Text)
    drawing_name: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="pending")  # pending|parsing|review|done|failed
    result: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class HistorySnapshot(Base):
    __tablename__ = "history_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    parse_job_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("parse_jobs.id"))
    drawing_oid: Mapped[str] = mapped_column(Text)
    template_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    db_version: Mapped[dict] = mapped_column(JSON, default=dict)
    rule_version: Mapped[dict] = mapped_column(JSON, default=dict)
    ai_raw_result: Mapped[dict] = mapped_column(JSON, default=dict)
    manual_edits: Mapped[dict] = mapped_column(JSON, default=dict)
    output_oid: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
