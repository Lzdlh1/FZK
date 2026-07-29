import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Integer, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Variable(Base):
    __tablename__ = "variables"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    template_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("templates.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(Text)
    placeholder: Mapped[str] = mapped_column(Text)
    sheet: Mapped[str] = mapped_column(Text)
    cell: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(Text)  # extract|database|formula|manual
    data_type: Mapped[str] = mapped_column(Text)  # string|number|integer|enum
    unit: Mapped[str | None] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    depends_on: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), server_default=text("'{}'"))

    __table_args__ = (UniqueConstraint("template_id", "name", name="uq_variables_template_name"),)


class VariablePrompt(Base):
    __tablename__ = "variable_prompts"

    variable_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("variables.id", ondelete="CASCADE"), primary_key=True)
    prompt: Mapped[str] = mapped_column(Text)
    output_constraints: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    confidence_threshold: Mapped[float] = mapped_column(Float, default=0.7, server_default=text("0.7"))
    post_process: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))


class FewShotRef(Base):
    __tablename__ = "few_shot_refs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    variable_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("variables.id", ondelete="CASCADE"))
    image_oid: Mapped[str] = mapped_column(Text)
    expected_json: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))


class Mapping(Base):
    __tablename__ = "mappings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    template_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("templates.id", ondelete="CASCADE"))
    drawing_field: Mapped[str] = mapped_column(Text)
    variable_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("variables.id"))
    auto_matched: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
