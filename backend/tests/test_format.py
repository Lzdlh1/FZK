"""format 模块单测:用 reportlab 生成最小 PDF,验证文本层提取与页面渲染。"""

import io

import pytest

from app.services.parse.format import (
    detect_text_layer,
    extract_pdf_text,
    format_split,
    render_pdf_pages,
)


@pytest.fixture(scope="module")
def sample_pdf_bytes() -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setFont("Helvetica", 24)
    c.drawString(100, 700, "DJ7021-1.5-11")
    c.showPage()
    c.save()
    return buf.getvalue()


def test_extract_pdf_text_returns_target_word(sample_pdf_bytes):
    text_map = extract_pdf_text(sample_pdf_bytes)
    assert text_map, "text_map 不应为空"
    texts = [item["text"] for item in text_map]
    # 抽取出的词中应能拼出目标字符串(reportlab 输出的可能是整串或分词)
    joined = "".join(texts)
    assert "DJ7021" in joined, f"未提取到目标文本,得到: {texts}"


def test_extract_pdf_text_bbox_normalized(sample_pdf_bytes):
    text_map = extract_pdf_text(sample_pdf_bytes)
    for item in text_map:
        bbox = item.get("bbox")
        assert bbox is not None, "bbox 不应为 None"
        assert len(bbox) == 4
        for v in bbox:
            assert 0.0 <= v <= 1.0, f"bbox 值超出 [0,1]: {bbox}"
        assert item["page"] == 1


def test_render_pdf_pages_returns_jpeg(sample_pdf_bytes):
    images = render_pdf_pages(sample_pdf_bytes, dpi=150)
    assert images, "渲染结果不应为空"
    assert len(images) == 1
    jpeg = images[0]
    assert jpeg[:2] == b"\xff\xd8", "渲染结果应为 JPEG (FFD8 开头)"
    assert len(jpeg) > 100


def test_detect_text_layer_true(sample_pdf_bytes):
    assert detect_text_layer(sample_pdf_bytes) is True


def test_format_split_pdf(sample_pdf_bytes):
    split = format_split("application/pdf", sample_pdf_bytes, "drawing.pdf")
    assert split["source_kind"] == "pdf"
    assert split["images"], "PDF 分流应产出图片"
    assert split["text_map"], "PDF 分流应产出文字地图"


def test_format_split_unsupported():
    from app.services.parse.format import UnsupportedFormatError

    with pytest.raises(UnsupportedFormatError):
        format_split("application/octet-stream", b"not-a-real-file", "x.bin")
