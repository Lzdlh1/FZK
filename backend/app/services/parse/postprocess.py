"""抽取结果后处理:单位剥离、大小写归一、DB 匹配、region 融合、置信度归一。"""

from __future__ import annotations

import re


def normalize_confidence(c) -> float:
    """置信度归一到 [0,1];None 给 0.5。"""
    if c is None:
        return 0.5
    try:
        v = float(c)
    except (TypeError, ValueError):
        return 0.5
    if v > 1.0:
        return 1.0
    if v < 0.0:
        return 0.0
    return v


def strip_unit(value, unit_pattern: str | None) -> str | None:
    """按正则去掉单位。值非字符串时原样返回。"""
    if value is None:
        return None
    if not unit_pattern:
        return value
    if not isinstance(value, str):
        return value
    try:
        return re.sub(unit_pattern, "", value).strip()
    except re.error:
        return value


def case_normalize(value, mode: str | None):
    """大小写归一:upper/lower/None。非字符串原样返回。"""
    if value is None or not mode or not isinstance(value, str):
        return value
    if mode == "upper":
        return value.upper()
    if mode == "lower":
        return value.lower()
    return value


def db_match(value, db_params_list: list[dict]) -> tuple[str | None, dict | None]:
    """与 database_params 精确匹配(按 value 字段)。

    db_params_list 元素形如 {value, category, model, field, version, unit}。
    返回 (matched_value, matched_record_or_None)。
    """
    if value is None:
        return None, None
    target = str(value).strip()
    if not target:
        return None, None
    for rec in db_params_list or []:
        rec_val = rec.get("value")
        if rec_val is None:
            continue
        if str(rec_val).strip() == target:
            return rec_val, rec
    return None, None


def fuse_region(field_value, text_map: list[dict] | None) -> dict | None:
    """若 value 命中文本地图某字符串,继承其 bbox;否则 None。"""
    if field_value is None or not text_map:
        return None
    target = str(field_value).strip()
    if not target:
        return None
    for item in text_map:
        text = (item.get("text") or "").strip()
        if text and (target == text or target in text or text in target):
            bbox = item.get("bbox")
            page = item.get("page", 1)
            if bbox:
                return {"page": page, "bbox": bbox}
            return {"page": page, "bbox": None}
    return None
