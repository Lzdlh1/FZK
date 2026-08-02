"""AI 学习训练样本:按模板组织的 few-shot 示例(图纸图片 + 期望解析结果)。"""

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.db.types import GUID


class LearnSample(Base):
    """对话式训练的 few-shot 样本。

    - template_id: 样本归属模板;解析该模板时注入其样本
    - image_oid:   示例图纸在对象存储中的 OID
    - expected_json: 期望解析结果,形如 {"fields": {"字段名": {"value": 值}, ...}}
      与 AI 输出 schema 一致,便于作为示例注入 prompt
    - sort_order:  排序序号,最新的值最大(解析时取最近 N 个)
    """

    __tablename__ = "learn_samples"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("templates.id", ondelete="CASCADE")
    )
    image_oid: Mapped[str] = mapped_column(Text)
    expected_json: Mapped[dict] = mapped_column(JSON, default=dict)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
