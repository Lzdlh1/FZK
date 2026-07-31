/**
 * Univer 快照与 xlsx 互转工具。
 * univer_snapshot 是 Univer 的 IWorkbookData 序列化 JSON,前端负责加载/保存。
 * 为避免与 Univer 内部类型深度耦合,此处使用宽松的本地类型 + 必要的 any 断言。
 *
 * 导入使用 exceljs(可读取样式/合并/公式/列宽行高),导出仍用 SheetJS。
 */
import * as XLSX from 'xlsx'
import ExcelJS from 'exceljs'

/** 单元格数据(Univer ICellData 的最小子集) */
export interface ICellData {
  v?: string | number | boolean | null
  t?: number | string
  f?: string
  s?: string | Record<string, unknown> | null
  // 允许携带其它 Univer 字段
  [key: string]: unknown
}

/** 工作表数据 */
export interface IWorksheetData {
  id: string
  name: string
  cellData: Record<number, Record<number, ICellData>>
  rowCount?: number
  columnCount?: number
  mergeData?: unknown[]
  rowData?: Record<number, Record<string, unknown>>
  columnData?: Record<number, Record<string, unknown>>
  defaultRowHeight?: number
  defaultColumnWidth?: number
  [key: string]: unknown
}

/** Univer 工作簿快照(对应 IWorkbookData) */
export interface IUniverSnapshot {
  id: string
  name?: string
  sheetOrder?: string[]
  sheets: Record<string, IWorksheetData>
  appVersion?: string
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  styles?: Record<string, any>
  resources?: unknown
  [key: string]: unknown
}

const DEFAULT_SHEET_ID = 'sheet-1'
const DEFAULT_SHEET_NAME = 'Sheet1'
const DEFAULT_WORKBOOK_ID = 'workbook-1'

/** 创建空快照(单 sheet "Sheet1") */
export function createEmptySnapshot(): IUniverSnapshot {
  return {
    id: DEFAULT_WORKBOOK_ID,
    sheetOrder: [DEFAULT_SHEET_ID],
    sheets: {
      [DEFAULT_SHEET_ID]: {
        id: DEFAULT_SHEET_ID,
        name: DEFAULT_SHEET_NAME,
        cellData: {},
        rowCount: 100,
        columnCount: 26,
      },
    },
    appVersion: '0.0.0',
    styles: {},
    resources: [],
  }
}

/** 加载快照到 Univer 实例,返回 workbook facade */
export function loadSnapshot(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  univerAPI: any,
  snapshot: IUniverSnapshot
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
): any {
  return univerAPI.createWorkbook(snapshot)
}

/** 导出当前活动工作簿快照 */
export function exportSnapshot(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  univerAPI: any
): IUniverSnapshot | null {
  const wb = univerAPI.getActiveWorkbook()
  if (!wb) return null
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return wb.save() as any
}

/**
 * 将行列号(0-based)转换为 A1 引用,如 (0,0)->"A1"。
 */
export function rowColToA1(row: number, col: number): string {
  let c = col
  let colStr = ''
  do {
    const rem = c % 26
    colStr = String.fromCharCode(65 + rem) + colStr
    c = Math.floor(c / 26) - 1
  } while (c >= 0)
  return `${colStr}${row + 1}`
}

/**
 * 将 A1 引用(如 "AB12")转为 {row, col}(0-based)。失败返回 null。
 */
export function a1ToRowCol(a1: string): { row: number; col: number } | null {
  const m = /^([A-Za-z]+)(\d+)$/.exec(a1.trim())
  if (!m) return null
  const letters = m[1].toUpperCase()
  let col = 0
  for (let i = 0; i < letters.length; i++) {
    col = col * 26 + (letters.charCodeAt(i) - 64)
  }
  col -= 1
  const row = parseInt(m[2], 10) - 1
  return { row, col }
}

// exceljs 边框样式字符串 -> Univer BorderStyleTypes 数字
// (THIN=1, HAIR=2, DOTTED=3, DASHED=4, DASH_DOT=5, DASH_DOT_DOT=6,
//  DOUBLE=7, MEDIUM=8, MEDIUM_DASHED=9, MEDIUM_DASH_DOT=10,
//  MEDIUM_DASH_DOT_DOT=11, SLANT_DASH_DOT=12, THICK=13)
const BORDER_STYLE_MAP: Record<string, number> = {
  thin: 1, hair: 2, dotted: 3, dashed: 4, dashDot: 5, dashDotDot: 6,
  double: 7, medium: 8, mediumDashed: 9, mediumDashDot: 10,
  mediumDashDotDot: 11, slantDashDot: 12, thick: 13,
}

// exceljs 颜色对象 -> Univer { rgb: '#RRGGBB' }
type ExcelColor = { argb?: string; theme?: number; tint?: number; indexed?: number } | null | undefined

function toUniverColor(color: ExcelColor): { rgb: string } | null {
  if (!color) return null
  const argb = typeof color.argb === 'string' ? color.argb : null
  if (argb) {
    // argb 形如 'FFRRGGBB',去掉前两位 alpha
    const rgb = argb.length === 8 ? argb.slice(2) : argb
    return { rgb: '#' + rgb.toUpperCase() }
  }
  // theme/indexed 颜色无法精确还原,留空让 Univer 用默认色
  return null
}

// exceljs 单元格 -> Univer 样式对象(仅含已设置的字段)
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function buildUniverStyle(cell: ExcelJS.Cell): Record<string, any> | null {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const s: Record<string, any> = {}
  const font = cell.font
  if (font) {
    if (font.name) s.ff = font.name
    if (font.size) s.fs = font.size
    if (font.bold) s.bl = 1
    if (font.italic) s.it = 1
    if (font.underline) s.ul = { s: 1 }
    if (font.strike) s.st = { s: 1 }
    if (font.color) {
      const c = toUniverColor(font.color as ExcelColor)
      if (c) s.cl = c
    }
  }
  const fill = cell.fill as
    | { type?: string; pattern?: string; fgColor?: ExcelColor }
    | undefined
  if (fill && fill.type === 'pattern' && fill.pattern === 'solid') {
    const c = toUniverColor(fill.fgColor)
    if (c) s.bg = c
  }
  const border = cell.border as {
    top?: { style?: string; color?: ExcelColor }
    bottom?: { style?: string; color?: ExcelColor }
    left?: { style?: string; color?: ExcelColor }
    right?: { style?: string; color?: ExcelColor }
  } | undefined
  if (border) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const bd: Record<string, any> = {}
    const sides: Array<['top' | 'bottom' | 'left' | 'right', 't' | 'b' | 'l' | 'r']> = [
      ['top', 't'],
      ['bottom', 'b'],
      ['left', 'l'],
      ['right', 'r'],
    ]
    for (const [src, dst] of sides) {
      const b = border[src]
      if (b && b.style && b.style !== 'none') {
        const styleNum = BORDER_STYLE_MAP[b.style]
        if (styleNum) {
          bd[dst] = { s: styleNum, cl: toUniverColor(b.color) || { rgb: '#000000' } }
        }
      }
    }
    if (Object.keys(bd).length) s.bd = bd
  }
  const align = cell.alignment as {
    horizontal?: string
    vertical?: string
    wrapText?: boolean
    textRotation?: number
  } | undefined
  if (align) {
    const ha = align.horizontal
    if (ha === 'left') s.ht = 1
    else if (ha === 'center' || ha === 'centerContinuous') s.ht = 2
    else if (ha === 'right') s.ht = 3
    else if (ha === 'justify' || ha === 'distributed') s.ht = 4
    const va = align.vertical
    if (va === 'top') s.vt = 1
    else if (va === 'middle' || va === 'center') s.vt = 2
    else if (va === 'bottom') s.vt = 3
    if (align.wrapText) s.tb = 3 // WRAP
    if (align.textRotation) s.tr = { a: align.textRotation }
  }
  if (cell.numFmt) {
    s.n = { pattern: cell.numFmt }
  }
  return Object.keys(s).length ? s : null
}

// exceljs 单元格值 -> { v, f }(公式与值)
function extractCellValue(
  cell: ExcelJS.Cell
): { v?: string | number | boolean; f?: string } {
  const result: { v?: string | number | boolean; f?: string } = {}
  const val = cell.value as unknown
  if (val === null || val === undefined) return result
  // 公式对象 { formula, result } 或 { sharedFormula, result }
  if (typeof val === 'object' && !Array.isArray(val) && !(val instanceof Date)) {
    const obj = val as {
      formula?: string
      sharedFormula?: string
      result?: unknown
      text?: string
      error?: string
    }
    if (obj.formula) {
      result.f = '=' + obj.formula
      if (obj.result !== undefined && obj.result !== null) {
        result.v = obj.result as string | number | boolean
      }
      return result
    }
    if (obj.sharedFormula) {
      result.f = '=' + obj.sharedFormula
      if (obj.result !== undefined && obj.result !== null) {
        result.v = obj.result as string | number | boolean
      }
      return result
    }
    if (obj.error) {
      result.v = obj.error
      return result
    }
    if (typeof obj.text === 'string') {
      result.v = obj.text
      return result
    }
    // 富文本等其它对象:跳过
    return result
  }
  if (val instanceof Date) {
    // 日期转成 YYYY-MM-DD 文本(简化处理,避免 Excel 序列号换算)
    const d = val
    const m = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    result.v = `${d.getFullYear()}-${m}-${day}`
    return result
  }
  result.v = val as string | number | boolean
  return result
}

// 解析 'A1:B2' -> { startRow, endRow, startColumn, endColumn }(0-based)
function parseMergeRange(range: string): {
  startRow: number
  endRow: number
  startColumn: number
  endColumn: number
} | null {
  const parts = range.split(':')
  if (parts.length !== 2) return null
  const s = a1ToRowCol(parts[0])
  const e = a1ToRowCol(parts[1])
  if (!s || !e) return null
  return {
    startRow: s.row,
    endRow: e.row,
    startColumn: s.col,
    endColumn: e.col,
  }
}

/**
 * 从 xlsx 文件导入为 Univer 快照(单 sheet:取第一个 sheet)。
 * 使用 exceljs 解析,保留公式、合并单元格、样式(字体/颜色/边框/对齐/数字格式)、
 * 列宽与行高。条件格式 exceljs 社区版读取受限,暂不导入。
 */
export async function importXlsx(file: File): Promise<IUniverSnapshot> {
  const buf = await file.arrayBuffer()
  const wb = new ExcelJS.Workbook()
  await wb.xlsx.load(buf)
  const ws = wb.worksheets[0]
  if (!ws) {
    return createEmptySnapshot()
  }

  const cellData: Record<number, Record<number, ICellData>> = {}
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const styles: Record<string, any> = {}
  let styleCounter = 0
  const styleCache = new Map<string, string>()
  let maxRow = 0
  let maxCol = 0

  ws.eachRow({ includeEmpty: true }, (row, rowNum) => {
    const r = rowNum - 1
    row.eachCell({ includeEmpty: true }, (cell, colNum) => {
      const c = colNum - 1
      const cellObj: ICellData = {}
      const val = extractCellValue(cell)
      if (val.f !== undefined) cellObj.f = val.f
      if (val.v !== undefined) cellObj.v = val.v
      // 样式
      const style = buildUniverStyle(cell)
      if (style) {
        const key = JSON.stringify(style)
        let styleId = styleCache.get(key)
        if (!styleId) {
          styleId = String(styleCounter++)
          styles[styleId] = style
          styleCache.set(key, styleId)
        }
        cellObj.s = styleId
      }
      if (Object.keys(cellObj).length) {
        if (!cellData[r]) cellData[r] = {}
        cellData[r][c] = cellObj
        if (r > maxRow) maxRow = r
        if (c > maxCol) maxCol = c
      }
    })
  })

  // 合并单元格(exceljs 存于 ws.model.merges,形如 ['A1:B2', ...])
  const mergeData: unknown[] = []
  const merges = (ws.model?.merges as string[] | undefined) ?? []
  for (const m of merges) {
    const parsed = parseMergeRange(m)
    if (parsed) mergeData.push(parsed)
  }

  // 列宽:exceljs width 为字符单位,Univer 的 w 为像素,需换算。
  // 近似公式 px = width * 7 + 5(基于 Calibri 11pt,MDW≈7px)
  const columnData: Record<number, Record<string, unknown>> = {}
  try {
    ws.columns.forEach((col) => {
      const colIdx = (col.number ?? 1) - 1
      if (typeof col.width === 'number' && col.width > 0) {
        columnData[colIdx] = { w: Math.round(col.width * 7 + 5) }
      }
    })
  } catch {
    // ignore
  }

  // 行高(exceljs 单位为 points,Univer 用像素;做 pt->px 近似换算)
  const rowData: Record<number, Record<string, unknown>> = {}
  ws.eachRow({ includeEmpty: false }, (row, rowNum) => {
    const r = rowNum - 1
    if (typeof row.height === 'number' && row.height > 0) {
      rowData[r] = { h: Math.round((row.height * 4) / 3) }
    }
  })

  const snapshot: IUniverSnapshot = {
    id: DEFAULT_WORKBOOK_ID,
    sheetOrder: [DEFAULT_SHEET_ID],
    sheets: {
      [DEFAULT_SHEET_ID]: {
        id: DEFAULT_SHEET_ID,
        name: ws.name || DEFAULT_SHEET_NAME,
        cellData,
        rowCount: Math.max(maxRow + 20, 100),
        columnCount: Math.max(maxCol + 5, 26),
        mergeData,
        rowData,
        columnData,
      },
    },
    appVersion: '0.0.0',
    styles,
    resources: [],
  }
  return snapshot
}

/**
 * 将快照导出为 xlsx 文件并触发下载。
 */
export function exportXlsx(
  snapshot: IUniverSnapshot,
  filename: string
): void {
  const sheetId = snapshot.sheetOrder?.[0] ?? Object.keys(snapshot.sheets)[0]
  const sheet = snapshot.sheets[sheetId]
  const cellData = sheet?.cellData ?? {}
  // 转换 cellData -> AoA
  const rows = Object.keys(cellData).map((r) => parseInt(r, 10))
  const maxRow = rows.length ? Math.max(...rows) : 0
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const aoa: any[][] = []
  for (let r = 0; r <= maxRow; r++) {
    const row = cellData[r]
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const arr: any[] = []
    if (row) {
      const cols = Object.keys(row).map((c) => parseInt(c, 10))
      const maxCol = cols.length ? Math.max(...cols) : 0
      for (let c = 0; c <= maxCol; c++) {
        const cell = row[c]
        arr.push(cell ? cell.v : null)
      }
    }
    aoa.push(arr)
  }
  const ws = XLSX.utils.aoa_to_sheet(aoa)
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, sheet?.name || DEFAULT_SHEET_NAME)
  const name = filename.endsWith('.xlsx') ? filename : `${filename}.xlsx`
  XLSX.writeFile(wb, name)
}
