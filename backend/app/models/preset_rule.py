import uuid

from sqlalchemy import Boolean, Integer, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class PresetRule(Base):
    __tablename__ = "preset_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(Text)
    expression_template: Mapped[str] = mapped_column(Text)
    params: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    output_unit: Mapped[str] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    version: Mapped[int] = mapped_column(Integer, default=1, server_default=text("1"))
    built_in: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
