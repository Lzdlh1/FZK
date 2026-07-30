/**
 * Univer 快照与 xlsx 互转工具。
 * univer_snapshot 是 Univer 的 IWorkbookData 序列化 JSON,前端负责加载/保存。
 * 为避免与 Univer 内部类型深度耦合,此处使用宽松的本地类型 + 必要的 any 断言。
 */
import * as XLSX from 'xlsx'

/** 单元格数据(Univer ICellData 的最小子集) */
export interface ICellData {
  v?: string | number | boolean | null
  t?: number | string
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
  [key: string]: unknown
}

/** Univer 工作簿快照(对应 IWorkbookData) */
export interface IUniverSnapshot {
  id: string
  name?: string
  sheetOrder?: string[]
  sheets: Record<string, IWorksheetData>
  appVersion?: string
  styles?: unknown
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

/**
 * 从 xlsx 文件导入为 Univer 快照(单 sheet:取第一个 sheet,填入 cellData)。
 */
export async function importXlsx(file: File): Promise<IUniverSnapshot> {
  const buf = await file.arrayBuffer()
  const wb = XLSX.read(buf, { type: 'array' })
  const firstSheetName = wb.SheetNames[0]
  const sheet = wb.Sheets[firstSheetName]
  // header:1 返回二维数组(每行一个数组)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const aoa: any[][] = XLSX.utils.sheet_to_json(sheet, {
    header: 1,
    raw: true,
    defval: null,
  })
  const cellData: Record<number, Record<number, ICellData>> = {}
  let maxRow = 0
  let maxCol = 0
  for (let r = 0; r < aoa.length; r++) {
    const row = aoa[r]
    if (!row) continue
    for (let c = 0; c < row.length; c++) {
      const v = row[c]
      if (v === null || v === undefined || v === '') continue
      if (!cellData[r]) cellData[r] = {}
      cellData[r][c] = { v }
      if (r > maxRow) maxRow = r
      if (c > maxCol) maxCol = c
    }
  }
  const snapshot: IUniverSnapshot = {
    id: DEFAULT_WORKBOOK_ID,
    sheetOrder: [DEFAULT_SHEET_ID],
    sheets: {
      [DEFAULT_SHEET_ID]: {
        id: DEFAULT_SHEET_ID,
        name: firstSheetName || DEFAULT_SHEET_NAME,
        cellData,
        rowCount: Math.max(maxRow + 20, 100),
        columnCount: Math.max(maxCol + 5, 26),
      },
    },
    appVersion: '0.0.0',
    styles: {},
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
