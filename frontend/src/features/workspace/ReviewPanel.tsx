import { useMemo, useState } from 'react'
import {
  Table,
  Input,
  InputNumber,
  Button,
  Tag,
  Tooltip,
  Space,
  message,
  Typography,
  Alert,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { parseJobApi } from '@/lib/api/parseJobs'
import type {
  ParseJobOut,
  FieldResult,
  TemplateVariable,
  ParseJobResult,
} from '@/types'

const { Text } = Typography

const STATUS_COLOR: Record<string, string> = {
  extracted: 'default',
  low_confidence: 'warning',
  not_found: 'error',
  error: 'error',
  manual: 'processing',
  formula: 'default',
}

const STATUS_TEXT: Record<string, string> = {
  extracted: '已识别',
  low_confidence: '低置信',
  not_found: '未找到',
  error: '错误',
  manual: '手动',
  formula: '公式',
}

interface ReviewPanelProps {
  job: ParseJobOut
  onChanged: (job: ParseJobOut) => void
}

interface FieldRow {
  name: string
  variable?: TemplateVariable
  field: FieldResult
}

const DEFAULT_THRESHOLD = 0.7

function getThreshold(variable?: TemplateVariable): number {
  return variable?.prompt?.confidence_threshold ?? DEFAULT_THRESHOLD
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return ''
  if (typeof value === 'number' || typeof value === 'string') return String(value)
  try {
    return JSON.stringify(value)
  } catch {
    return String(value)
  }
}

export default function ReviewPanel({ job, onChanged }: ReviewPanelProps) {
  const templateVars = job.template?.variables ?? []

  /** 本地修改的字段值:name -> value */
  const [edits, setEdits] = useState<Record<string, unknown>>({})
  /** 手动改过的字段名集合 */
  const [manualOverrides, setManualOverrides] = useState<Set<string>>(
    () => new Set()
  )
  const [saving, setSaving] = useState(false)
  const [rerunning, setRerunning] = useState<Record<string, boolean>>({})

  const rows: FieldRow[] = useMemo(() => {
    const fields = job.result?.fields ?? {}
    return Object.entries(fields).map(([name, field]) => {
      const variable = templateVars.find((v) => v.name === name)
      return { name, variable, field }
    })
  }, [job, templateVars])

  const hasEdits = Object.keys(edits).length > 0

  const handleValueChange = (name: string, value: unknown) => {
    setEdits((prev) => ({ ...prev, [name]: value }))
    setManualOverrides((prev) => {
      const next = new Set(prev)
      next.add(name)
      return next
    })
  }

  const handleRerun = async (name: string, variableId: string) => {
    setRerunning((prev) => ({ ...prev, [name]: true }))
    try {
      const res = await parseJobApi.rerunField(job.id, variableId)
      const newField = res.field
      const oldResult: ParseJobResult = job.result ?? {
        fields: {},
        meta: {},
        error: null,
      }
      const newFields = { ...oldResult.fields, [name]: newField }
      const newJob: ParseJobOut = {
        ...job,
        result: { ...oldResult, fields: newFields },
      }
      onChanged(newJob)
      // 清除该字段的本地编辑与手动标记
      setEdits((prev) => {
        const next = { ...prev }
        delete next[name]
        return next
      })
      setManualOverrides((prev) => {
        const next = new Set(prev)
        next.delete(name)
        return next
      })
      message.success(`字段「${name}」已重新识别`)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '重新识别失败'
      message.error(msg)
    } finally {
      setRerunning((prev) => ({ ...prev, [name]: false }))
    }
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const updated = await parseJobApi.review(
        job.id,
        edits,
        Array.from(manualOverrides)
      )
      onChanged(updated)
      setEdits({})
      setManualOverrides(new Set())
      message.success('审核已保存')
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '保存失败'
      message.error(msg)
    } finally {
      setSaving(false)
    }
  }

  const columns: ColumnsType<FieldRow> = [
    {
      title: '变量名',
      dataIndex: 'name',
      key: 'name',
      width: 150,
      render: (name: string, row) => (
        <div>
          <div style={{ fontWeight: 500 }}>{name}</div>
          {row.variable?.placeholder && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              {row.variable.placeholder}
            </Text>
          )}
        </div>
      ),
    },
    {
      title: '来源',
      key: 'source',
      width: 90,
      render: (_, row) => row.variable?.source_type ?? '—',
    },
    {
      title: '值',
      key: 'value',
      render: (_, row) => {
        const currentValue = row.name in edits ? edits[row.name] : row.field.value
        const isNumber = typeof row.field.value === 'number'
        if (isNumber) {
          return (
            <InputNumber
              value={currentValue as number}
              onChange={(v) => handleValueChange(row.name, v)}
              size="small"
              style={{ width: '100%' }}
            />
          )
        }
        return (
          <Input
            value={formatValue(currentValue)}
            onChange={(e) => handleValueChange(row.name, e.target.value)}
            size="small"
          />
        )
      },
    },
    {
      title: '置信度',
      key: 'confidence',
      width: 90,
      render: (_, row) => {
        if (row.field.confidence == null) {
          return <Text type="secondary">—</Text>
        }
        const threshold = getThreshold(row.variable)
        const low = row.field.confidence < threshold
        return (
          <Tooltip title={low ? `低于阈值 ${threshold}` : undefined}>
            <Text
              style={
                low
                  ? { color: '#faad14', fontWeight: 600 }
                  : undefined
              }
            >
              {(row.field.confidence * 100).toFixed(0)}%
            </Text>
          </Tooltip>
        )
      },
    },
    {
      title: '状态',
      key: 'status',
      width: 90,
      render: (_, row) => {
        const status = manualOverrides.has(row.name)
          ? 'manual'
          : row.field.status
        return (
          <Tag color={STATUS_COLOR[status] ?? 'default'}>
            {STATUS_TEXT[status] ?? status}
          </Tag>
        )
      },
    },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      render: (_, row) => {
        const isExtract = row.variable?.source_type === 'extract'
        if (!isExtract || !row.variable) return null
        return (
          <Button
            size="small"
            type="link"
            loading={!!rerunning[row.name]}
            onClick={() => handleRerun(row.name, row.variable!.id)}
          >
            重新识别
          </Button>
        )
      },
    },
  ]

  return (
    <div style={{ padding: 12 }}>
      {rows.length === 0 ? (
        <Alert
          type="warning"
          showIcon
          message="无字段结果"
          description={
            job.result?.error ?? '该任务尚未产出字段,请先执行解析。'
          }
        />
      ) : (
        <Table
          columns={columns}
          dataSource={rows}
          rowKey="name"
          size="small"
          pagination={false}
          expandable={{
            rowExpandable: (row) =>
              row.variable?.source_type === 'formula' &&
              (!!row.field.substituted_expression ||
                (!!row.field.db_refs && row.field.db_refs.length > 0)),
            expandedRowRender: (row) => (
              <div style={{ padding: '8px 12px', background: '#fafafa' }}>
                {row.field.substituted_expression && (
                  <div style={{ marginBottom: 4 }}>
                    <Text type="secondary">表达式:</Text>{' '}
                    <Text code>{row.field.substituted_expression}</Text>
                  </div>
                )}
                {row.field.db_refs && row.field.db_refs.length > 0 && (
                  <div>
                    <Text type="secondary">DB 参数:</Text>{' '}
                    <Space size={[4, 4]} wrap>
                      {row.field.db_refs.map((ref, i) => (
                        <Tag key={i} color="blue">
                          {ref.var}={formatValue(ref.value)} (v{ref.version})
                        </Tag>
                      ))}
                    </Space>
                  </div>
                )}
              </div>
            ),
          }}
        />
      )}

      <div
        style={{
          marginTop: 16,
          display: 'flex',
          gap: 8,
          justifyContent: 'flex-end',
          alignItems: 'center',
        }}
      >
        {hasEdits && (
          <Text type="secondary" style={{ fontSize: 12 }}>
            有 {Object.keys(edits).length} 项未保存修改
          </Text>
        )}
        <Button onClick={handleSave} loading={saving} disabled={!hasEdits}>
          保存审核
        </Button>
        <Tooltip title="输出功能在 1e 阶段实现">
          <Button type="primary" disabled>
            确认输出
          </Button>
        </Tooltip>
      </div>
    </div>
  )
}
