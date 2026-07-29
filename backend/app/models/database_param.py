import uuid

from sqlalchemy import Boolean, Integer, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class DatabaseParam(Base):
    __tablename__ = "database_params"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    category: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(Text)
    field: Mapped[str] = mapped_column(Text)
    value: Mapped[str] = mapped_column(Text)
    unit: Mapped[str | None] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    version: Mapped[int] = mapped_column(Integer, default=1, server_default=text("1"))

    __table_args__ = (UniqueConstraint("category", "model", "field", "version", name="uq_database_params_field"),)
