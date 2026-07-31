import uuid

from sqlalchemy import Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.db.types import GUID


class Rule(Base):
    __tablename__ = "rules"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    scope: Mapped[str | None] = mapped_column(Text)  # global|drawing_type:xxx
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
