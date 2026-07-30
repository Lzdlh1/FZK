import { forwardRef, useEffect, useImperativeHandle, useRef } from 'react'
import { createUniver, LocaleType, mergeLocales } from '@univerjs/presets'
import { UniverSheetsCorePreset } from '@univerjs/preset-sheets-core'
import zhCN from '@univerjs/preset-sheets-core/locales/zh-CN'
import '@univerjs/preset-sheets-core/lib/index.css'
import {
  createEmptySnapshot,
  type IUniverSnapshot,
} from '@/lib/univer/snapshot'

/** 选中单元格信息 */
export interface SelectedCell {
  sheet: string
  cell: string
}

/** 暴露给父组件的命令式句柄 */
export interface UniverSheetHandle {
  getSnapshot: () => IUniverSnapshot | null
  getActiveSheetName: () => string | null
  getActiveCell: () => SelectedCell | null
}

interface UniverSheetProps {
  initialSnapshot?: IUniverSnapshot | null
  onSelectionChange?: (sel: SelectedCell | null) => void
}

/**
 * Univer 表格组件(forwardRef)。
 * 负责创建/销毁 Univer 实例,加载快照,并暴露 getSnapshot 等方法。
 */
const UniverSheet = forwardRef<UniverSheetHandle, UniverSheetProps>(
  function UniverSheet({ initialSnapshot, onSelectionChange }, ref) {
    const containerRef = useRef<HTMLDivElement>(null)
    // Univer 实例与 API 使用宽松类型,避免与内部类型深度耦合
    const univerRef = useRef<{ dispose: () => void } | null>(null)
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const univerAPIRef = useRef<any>(null)
    const cbRef = useRef(onSelectionChange)
    cbRef.current = onSelectionChange

    useEffect(() => {
      const container = containerRef.current
      if (!container) return

      const { univer, univerAPI } = createUniver({
        locale: LocaleType.ZH_CN,
        locales: { zhCN: mergeLocales(zhCN) },
        presets: [UniverSheetsCorePreset({ container })],
      })
      univerRef.current = univer
      univerAPIRef.current = univerAPI

      const snap = initialSnapshot ?? createEmptySnapshot()
      // Univer createWorkbook 期望 Partial<IWorkbookData>,此处为边界转换
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      univerAPI.createWorkbook(snap as any)

      // 选中变化事件:读取当前活动单元格并回调
      const readSelection = () => {
        try {
          const wb = univerAPI.getActiveWorkbook()
          if (!wb) {
            cbRef.current?.(null)
            return
          }
          const sheet = wb.getActiveSheet().getSheetName()
          const range = wb.getActiveRange()
          const cell = range ? range.getA1Notation() : 'A1'
          cbRef.current?.({ sheet, cell })
        } catch {
          cbRef.current?.(null)
        }
      }

      let disposable: { dispose: () => void } | undefined
      try {
        disposable = univerAPI.addEvent(
          univerAPI.Event.SelectionChanged,
          () => readSelection()
        )
      } catch {
        // 事件 API 不可用时忽略,父组件可手动调用 getActiveCell
      }

      return () => {
        try {
          disposable?.dispose()
        } catch {
          // ignore
        }
        try {
          univer.dispose()
        } catch {
          // ignore
        }
        univerRef.current = null
        univerAPIRef.current = null
      }
      // 仅在挂载时创建一次 Univer 实例
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])

    useImperativeHandle(
      ref,
      () => ({
        getSnapshot() {
          const api = univerAPIRef.current
          if (!api) return null
          const wb = api.getActiveWorkbook()
          if (!wb) return null
          return wb.save() as IUniverSnapshot
        },
        getActiveSheetName() {
          const api = univerAPIRef.current
          if (!api) return null
          const wb = api.getActiveWorkbook()
          if (!wb) return null
          try {
            return wb.getActiveSheet().getSheetName()
          } catch {
            return null
          }
        },
        getActiveCell() {
          const api = univerAPIRef.current
          if (!api) return null
          const wb = api.getActiveWorkbook()
          if (!wb) return null
          try {
            const sheet = wb.getActiveSheet().getSheetName()
            const range = wb.getActiveRange()
            const cell = range ? range.getA1Notation() : 'A1'
            return { sheet, cell }
          } catch {
            return null
          }
        },
      }),
      []
    )

    return <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
  }
)

export default UniverSheet
