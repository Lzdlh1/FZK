"""内置预设规则 seed:启动时若 preset_rules 表为空则插入 3 条占位规则。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.preset_rule import PresetRule


SEED_RULES = [
    {
        "name": "开线长度",
        "category": "线材",
        "expression_template": "{L} - {eat} * {n}",
        "params": [
            {"key": "L", "label": "线材总长", "data_type": "number", "unit": "mm", "bind_kind": "variable"},
            {"key": "eat", "label": "吃线长度", "data_type": "number", "unit": "mm", "bind_kind": "variable_or_db"},
            {"key": "n", "label": "端子数", "data_type": "integer", "bind_kind": "variable"},
        ],
        "output_unit": "mm",
    },
    {
        "name": "焊接剥线长度",
        "category": "焊接",
        "expression_template": "{L} - {strip} * 2",
        "params": [
            {"key": "L", "label": "线芯长度", "data_type": "number", "unit": "mm", "bind_kind": "variable"},
            {"key": "strip", "label": "剥线长度", "data_type": "number", "unit": "mm", "bind_kind": "variable_or_db"},
        ],
        "output_unit": "mm",
    },
    {
        "name": "套管长度补偿",
        "category": "套管",
        "expression_template": "{L} + {comp}",
        "params": [
            {"key": "L", "label": "基础长度", "data_type": "number", "unit": "mm", "bind_kind": "variable"},
            {"key": "comp", "label": "补偿值", "data_type": "number", "unit": "mm", "bind_kind": "variable_or_db"},
        ],
        "output_unit": "mm",
    },
]


def seed_preset_rules(db: Session) -> None:
    """若 preset_rules 表为空,插入内置占位规则。已存在则跳过。"""
    if db.query(PresetRule).first() is not None:
        return
    for rule in SEED_RULES:
        db.add(PresetRule(built_in=True, version=1, enabled=True, **rule))
    db.commit()
