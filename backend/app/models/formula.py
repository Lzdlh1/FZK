import uuid

from sqlalchemy import JSON, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.db.types import GUID


class Formula(Base):
    __tablename__ = "formulas"

    variable_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("variables.id", ondelete="CASCADE"), primary_key=True)
    kind: Mapped[str] = mapped_column(Text)  # preset|custom
    expression: Mapped[str] = mapped_column(Text)
    preset_rule_id: Mapped[uuid.UUID | None] = mapped_column(GUID, ForeignKey("preset_rules.id"))
    dependencies: Mapped[list] = mapped_column(JSON, default=list)
