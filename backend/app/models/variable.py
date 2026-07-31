import uuid

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.db.types import GUID


class Variable(Base):
    __tablename__ = "variables"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("templates.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(Text)
    placeholder: Mapped[str] = mapped_column(Text)
    sheet: Mapped[str] = mapped_column(Text)
    cell: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(Text)  # extract|database|formula|manual
    data_type: Mapped[str] = mapped_column(Text)  # string|number|integer|enum
    unit: Mapped[str | None] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    depends_on: Mapped[list] = mapped_column(JSON, default=list)

    __table_args__ = (UniqueConstraint("template_id", "name", name="uq_variables_template_name"),)


class VariablePrompt(Base):
    __tablename__ = "variable_prompts"

    variable_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("variables.id", ondelete="CASCADE"), primary_key=True)
    prompt: Mapped[str] = mapped_column(Text)
    output_constraints: Mapped[dict] = mapped_column(JSON, default=dict)
    confidence_threshold: Mapped[float] = mapped_column(Float, default=0.7)
    post_process: Mapped[dict] = mapped_column(JSON, default=dict)


class FewShotRef(Base):
    __tablename__ = "few_shot_refs"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    variable_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("variables.id", ondelete="CASCADE"))
    image_oid: Mapped[str] = mapped_column(Text)
    expected_json: Mapped[dict] = mapped_column(JSON, default=dict)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Mapping(Base):
    __tablename__ = "mappings"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("templates.id", ondelete="CASCADE"))
    drawing_field: Mapped[str] = mapped_column(Text)
    variable_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("variables.id"))
    auto_matched: Mapped[bool] = mapped_column(Boolean, default=False)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
