import uuid

from sqlalchemy import Boolean, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Rule(Base):
    __tablename__ = "rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    scope: Mapped[str | None] = mapped_column(Text)  # global|drawing_type:xxx
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
