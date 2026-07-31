import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.db.types import GUID


class AIProvider(Base):
    __tablename__ = "ai_providers"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text)
    endpoint: Mapped[str] = mapped_column(Text)
    api_key_enc: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(Text)
    weight: Mapped[int] = mapped_column(Integer, default=1)
    healthy: Mapped[bool] = mapped_column(Boolean, default=True)
    last_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
