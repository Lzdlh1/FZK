import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ParseJob(Base):
    __tablename__ = "parse_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    template_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("templates.id"))
    drawing_oid: Mapped[str] = mapped_column(Text)
    drawing_name: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="pending", server_default=text("'pending'"))  # pending|parsing|review|done|failed
    result: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class HistorySnapshot(Base):
    __tablename__ = "history_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    parse_job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("parse_jobs.id"))
    drawing_oid: Mapped[str] = mapped_column(Text)
    template_snapshot: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    db_version: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    rule_version: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    ai_raw_result: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    manual_edits: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    output_oid: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
