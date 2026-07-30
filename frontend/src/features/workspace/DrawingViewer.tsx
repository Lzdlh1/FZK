import { useEffect, useState } from 'react'
import { Spin, Result, Alert } from 'antd'
import { getDrawingObjectUrl } from '@/lib/api/parseJobs'
import type { SourceRegion } from '@/types'

interface DrawingViewerProps {
  jobId: string
  /** 字段来源区域;传入时在图片上叠加红框(PDF 仅提示页码) */
  sourceRegion?: SourceRegion | null
}

interface DrawingState {
  url: string
  contentType: string
}

export default function DrawingViewer({
  jobId,
  sourceRegion,
}: DrawingViewerProps) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [drawing, setDrawing] = useState<DrawingState | null>(null)

  useEffect(() => {
    let objectUrl: string | null = null
    let cancelled = false
    setLoading(true)
    setError(null)
    setDrawing(null)

    getDrawingObjectUrl(jobId)
      .then(({ url, contentType }) => {
        if (cancelled) {
          URL.revokeObjectURL(url)
          return
        }
        objectUrl = url
        setDrawing({ url, contentType })
        setLoading(false)
      })
      .catch((e: unknown) => {
        if (cancelled) return
        const msg = e instanceof Error ? e.message : '加载图纸失败'
        setError(msg)
        setLoading(false)
      })

    return () => {
      cancelled = true
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl)
        objectUrl = null
      }
    }
  }, [jobId])

  if (loading) {
    return (
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          padding: 48,
        }}
      >
        <Spin tip="加载图纸中..." />
      </div>
    )
  }

  if (error || !drawing) {
    return (
      <Result
        status="error"
        title="图纸加载失败"
        subTitle={error ?? '未知错误'}
      />
    )
  }

  const isPdf = drawing.contentType.toLowerCase().includes('pdf')
  const hasRegion = !!sourceRegion && !!sourceRegion.bbox

  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        height: '100%',
        minHeight: 400,
        overflow: 'auto',
        background: '#fafafa',
      }}
    >
      {isPdf ? (
        <>
          <iframe
            src={drawing.url}
            title="图纸预览"
            style={{
              width: '100%',
              height: '100%',
              minHeight: 600,
              border: 'none',
            }}
          />
          {hasRegion && (
            <div style={{ padding: '4px 12px' }}>
              <Alert
                type="info"
                showIcon
                message={`来源区域:第 ${sourceRegion!.page} 页`}
                description="PDF 多页预览暂不支持叠加选区框,请按页码定位。"
              />
            </div>
          )}
        </>
      ) : (
        <div
          style={{
            position: 'relative',
            display: 'inline-block',
            margin: '0 auto',
          }}
        >
          <img
            src={drawing.url}
            alt="图纸"
            style={{ display: 'block', maxWidth: '100%', height: 'auto' }}
          />
          {hasRegion && (
            <div
              style={{
                position: 'absolute',
                left: `${sourceRegion!.bbox[0] * 100}%`,
                top: `${sourceRegion!.bbox[1] * 100}%`,
                width: `${sourceRegion!.bbox[2] * 100}%`,
                height: `${sourceRegion!.bbox[3] * 100}%`,
                border: '2px solid rgba(255, 0, 0, 0.85)',
                background: 'rgba(255, 0, 0, 0.15)',
                pointerEvents: 'none',
                boxSizing: 'border-box',
              }}
            />
          )}
        </div>
      )}
    </div>
  )
}
