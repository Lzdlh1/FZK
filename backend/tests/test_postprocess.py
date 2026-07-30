"""postprocess 单测:strip_unit / case_normalize / normalize_confidence / db_match。"""

from app.services.parse.postprocess import (
    case_normalize,
    db_match,
    fuse_region,
    normalize_confidence,
    strip_unit,
)


def test_strip_unit():
    assert strip_unit("12mm", r"mm") == "12"
    assert strip_unit("3.5 m", r"\s?m") == "3.5"
    assert strip_unit("abc", None) == "abc"
    assert strip_unit(None, r"mm") is None
    assert strip_unit(123, r"mm") == 123  # 非字符串原样返回


def test_case_normalize():
    assert case_normalize("abc", "upper") == "ABC"
    assert case_normalize("ABC", "lower") == "abc"
    assert case_normalize("AbC", None) == "AbC"
    assert case_normalize(None, "upper") is None
    assert case_normalize(123, "upper") == 123


def test_normalize_confidence():
    assert normalize_confidence(1.5) == 1.0
    assert normalize_confidence(-0.2) == 0.0
    assert normalize_confidence(0.7) == 0.7
    assert normalize_confidence(None) == 0.5
    assert normalize_confidence("not-a-number") == 0.5


def test_db_match_hit_and_miss():
    params = [
        {"value": "DJ7021-1.5-11", "category": "连接器", "model": "DJ7021", "field": "model", "version": 1},
        {"value": "DJ7021-2.0-21", "category": "连接器", "model": "DJ7021", "field": "alt", "version": 1},
    ]
    matched, rec = db_match("DJ7021-1.5-11", params)
    assert matched == "DJ7021-1.5-11"
    assert rec is not None and rec["model"] == "DJ7021"

    matched2, rec2 = db_match("not-exist", params)
    assert matched2 is None
    assert rec2 is None

    assert db_match(None, params) == (None, None)


def test_fuse_region():
    text_map = [
        {"text": "DJ7021-1.5-11", "bbox": [0.1, 0.2, 0.3, 0.05], "page": 1},
        {"text": "其它文字", "bbox": [0.5, 0.5, 0.1, 0.1], "page": 1},
    ]
    region = fuse_region("DJ7021-1.5-11", text_map)
    assert region is not None
    assert region["page"] == 1
    assert region["bbox"] == [0.1, 0.2, 0.3, 0.05]

    assert fuse_region("不存在", text_map) is None
    assert fuse_region("x", []) is None
