import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AIProvider(Base):
    __tablename__ = "ai_providers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name: Mapped[str] = mapped_column(Text)
    endpoint: Mapped[str] = mapped_column(Text)
    api_key_enc: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(Text)
    weight: Mapped[int] = mapped_column(Integer, default=1, server_default=text("1"))
    healthy: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    last_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
