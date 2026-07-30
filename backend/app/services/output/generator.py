"""最终输出 Excel 生成。

负责:
- 把审核后的字段值回填进 Univer 快照(``fill_snapshot_with_values``);
- 把填充后的快照转成 xlsx 字节流(``snapshot_to_xlsx_bytes``,后端独立用 openpyxl,
  不依赖前端 SheetJS;ADR#13 仅保留值,不写 Excel 公式);
- 输出文件名构造(``build_output_filename`` / ``sanitize_filename``)。

Univer 快照结构(对应前端 IUniverSnapshot / IWorkbookData):
    {
      "id": "workbook-1",
      "sheetOrder": ["s1", ...],
      "sheets": {
        "s1": {"id": "s1", "name": "Sheet1", "cellData": {rowIndex: {colIndex: {"v": value}}}},
        ...
      }
    }
行/列号从 0 开始;JSONB 反序列化后键为字符串,本模块读取时统一 ``int()`` 处理。
"""

from __future__ import annotations

import io
import os
import re
from datetime import datetime, timezone
from typing import Any

from openpyxl import Workbook

_ILLEGAL_FILENAME_CHARS = set('\\/:*?"<>|')
_A1_RE = re.compile(r"^([A-Za-z]+)(\d+)$")


def sanitize_filename(name: str) -> str:
    """过滤文件名非法字符 \\/:*?"<>| 替换为 _。空名回退为“输出”。"""
    if not name:
        return "输出"
    return "".join("_" if ch in _ILLEGAL_FILENAME_CHARS else ch for ch in name)


def build_output_filename(drawing_name: str, custom_name: str | None) -> str:
    """构造输出文件名:{基础名}_{YYYYMMDDHHMM}.xlsx(UTC,到分钟)。

    基础名:用户传入 custom_name,或“图纸名(去扩展名)+工艺辅助卡”。
    """
    if custom_name:
        base = custom_name
    else:
        stem = os.path.splitext(drawing_name)[0] if drawing_name else "输出"
        base = f"{stem}工艺辅助卡"
    base = sanitize_filename(base)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
    return f"{base}_{ts}.xlsx"


def a1_to_row_col(a1: str) -> tuple[int, int] | None:
    """A1 引用(如 "AB12")转 {row, col}(0-based);失败返回 None。"""
    if not a1:
        return None
    m = _A1_RE.match(a1.strip())
    if not m:
        return None
    letters = m.group(1).upper()
    col = 0
    for ch in letters:
        col = col * 26 + (ord(ch) - 64)
    col -= 1
    row = int(m.group(2)) - 1
    return row, col


def _get(obj: Any, key: str, default: Any = None) -> Any:
    """兼容 ORM 对象(属性)与 dict(键)读取。"""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _get_row(cell_data: dict, row: int) -> dict:
    """按行号取行 dict,兼容 int/str 键(JSONB 反序列化后为 str)。"""
    return cell_data.get(row) or cell_data.get(str(row)) or {}


def fill_snapshot_with_values(
    univer_snapshot: dict, variables: list, fields: dict
) -> dict:
    """把 fields[var.name] 的值写入快照对应 sheet+cell。

    - 仅处理 enabled 变量(缺省视为 True);
    - fields[var.name] 可为 {value: ...} dict 或裸值;value 为 None 则留空(跳过);
    - 通过变量 sheet 名称匹配 snapshot.sheets[*].name,cell 用 A1 定位;
    - 合并单元格的左上锚点由变量 cell 直接指定,无需特殊处理;
    - 返回填充后的新 snapshot(浅拷贝,不修改入参的 sheets 结构)。
    """
    snapshot = dict(univer_snapshot or {})
    sheets = dict(snapshot.get("sheets") or {})

    # 名称 -> sheetId 映射(同名取第一个)
    name_to_id: dict[str, str] = {}
    for sid, sheet in sheets.items():
        if isinstance(sheet, dict):
            sname = sheet.get("name", sid)
            name_to_id.setdefault(sname, sid)

    for var in variables or []:
        if _get(var, "enabled", True) is False:
            continue
        name = _get(var, "name")
        sheet_name = _get(var, "sheet")
        cell_ref = _get(var, "cell")
        if not name or not sheet_name or not cell_ref:
            continue

        fdata = (fields or {}).get(name)
        if fdata is None:
            continue
        value = fdata.get("value") if isinstance(fdata, dict) else fdata
        if value is None:
            continue

        rc = a1_to_row_col(cell_ref)
        if rc is None:
            continue
        row, col = rc

        sid = name_to_id.get(sheet_name) or (
            sheet_name if sheet_name in sheets else None
        )
        if sid is None:
            continue

        sheet = dict(sheets.get(sid) or {})
        cell_data = dict(sheet.get("cellData") or {})
        rrow = dict(_get_row(cell_data, row))
        rrow[col] = {"v": value}
        cell_data[row] = rrow
        sheet["cellData"] = cell_data
        sheets[sid] = sheet

    snapshot["sheets"] = sheets
    return snapshot


def _coerce_cell_value(v: Any) -> Any:
    """openpyxl 仅接受 str/int/float/bool/datetime;其余转字符串。"""
    if v is None:
        return None
    if isinstance(v, (str, int, float, bool)):
        return v
    return str(v)


def snapshot_to_xlsx_bytes(snapshot: dict) -> bytes:
    """把 Univer 快照转成 xlsx 字节流(仅写值,不复制样式/公式)。

    按 sheetOrder(缺失则 sheets 插入序)逐 sheet 创建 openpyxl 工作表,
    遍历 cellData 写入单元格(行列号 0-based -> openpyxl 1-based)。
    """
    snapshot = snapshot or {}
    sheets = snapshot.get("sheets") or {}
    order = snapshot.get("sheetOrder")
    if order:
        sheet_ids = [sid for sid in order if sid in sheets]
    else:
        sheet_ids = list(sheets.keys())

    wb = Workbook()
    default_ws = wb.active
    first = True
    for sid in sheet_ids:
        sheet = sheets.get(sid) or {}
        name = sheet.get("name") or sid
        if first:
            ws = default_ws
            ws.title = name
            first = False
        else:
            ws = wb.create_sheet(title=name)

        cell_data = sheet.get("cellData") or {}
        if not isinstance(cell_data, dict):
            continue
        for r_key, row in cell_data.items():
            try:
                r = int(r_key)
            except (ValueError, TypeError):
                continue
            if not isinstance(row, dict):
                continue
            for c_key, cell in row.items():
                try:
                    c = int(c_key)
                except (ValueError, TypeError):
                    continue
                value = cell.get("v") if isinstance(cell, dict) else cell
                value = _coerce_cell_value(value)
                if value is None:
                    continue
                ws.cell(row=r + 1, column=c + 1, value=value)

    if first:
        # 没有任何 sheet:保留默认空工作表,重命名为 Sheet1
        default_ws.title = "Sheet1"

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
