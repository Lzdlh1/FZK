import uuid

from sqlalchemy import Boolean, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.db.types import GUID


class DatabaseParam(Base):
    __tablename__ = "database_params"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    category: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(Text)
    field: Mapped[str] = mapped_column(Text)
    value: Mapped[str] = mapped_column(Text)
    unit: Mapped[str | None] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)

    __table_args__ = (UniqueConstraint("category", "model", "field", "version", name="uq_database_params_field"),)
