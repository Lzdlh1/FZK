import uuid

from sqlalchemy import ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Formula(Base):
    __tablename__ = "formulas"

    variable_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("variables.id", ondelete="CASCADE"), primary_key=True)
    kind: Mapped[str] = mapped_column(Text)  # preset|custom
    expression: Mapped[str] = mapped_column(Text)
    preset_rule_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("preset_rules.id"))
    dependencies: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), server_default=text("'{}'"))
