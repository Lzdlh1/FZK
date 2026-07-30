import { useEffect, useState } from 'react'
import {
  Layout,
  Spin,
  Result,
  Tag,
  Button,
  Space,
  Typography,
  message,
  Modal,
  Descriptions,
} from 'antd'
import { useNavigate, useParams } from 'react-router-dom'
import { parseJobApi } from '@/lib/api/parseJobs'
import type { ParseJobOut, ParseJobStatus, HistorySnapshotOut } from '@/types'
import DrawingViewer from './DrawingViewer'
import ReviewPanel from './ReviewPanel'

const { Header, Content } = Layout
const { Title, Text } = Typography

const STATUS_META: Record<ParseJobStatus, { color: string; text: string }> = {
  pending: { color: 'default', text: '待解析' },
  parsing: { color: 'processing', text: '解析中' },
  review: { color: 'warning', text: '待审核' },
  done: { color: 'success', text: '已输出' },
  failed: { color: 'error', text: '失败' },
}

function formatTime(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString()
}

/** 从 ai_raw_result 中提取 fields 计数 */
function getAiFieldCount(snapshot: HistorySnapshotOut): number {
  const fields = (snapshot.ai_raw_result as Record<string, unknown> | null)
    ?.fields as Record<string, unknown> | undefined
  return fields ? Object.keys(fields).length : 0
}

/** manual_edits 摘要:返回键数 */
function getManualEditCount(snapshot: HistorySnapshotOut): number {
  return Object.keys(snapshot.manual_edits ?? {}).length
}

export default function ReviewPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [job, setJob] = useState<ParseJobOut | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [history, setHistory] = useState<HistorySnapshotOut | null>(null)
  const [historyModalOpen, setHistoryModalOpen] = useState(false)

  useEffect(() => {
    if (!id) return
    setLoading(true)
    setError(null)
    setHistory(null)
    parseJobApi
      .get(id)
      .then((j) => {
        setJob(j)
      })
      .catch((e: unknown) => {
        const msg = e instanceof Error ? e.message : '加载任务失败'
        setError(msg)
      })
      .finally(() => setLoading(false))
  }, [id])

  // status='done' 时预加载历史快照(用于展示输出时间 + 历史快照 Modal)
  useEffect(() => {
    if (!id || !job || job.status !== 'done') {
      setHistory(null)
      return
    }
    let cancelled = false
    parseJobApi
      .getHistory(id)
      .then((snap) => {
        if (!cancelled) setHistory(snap)
      })
      .catch(() => {
        // 预加载失败静默处理,点按钮时可再试
      })
    return () => {
      cancelled = true
    }
  }, [id, job?.status])

  if (loading) {
    return (
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: '100vh',
        }}
      >
        <Spin size="large" />
      </div>
    )
  }

  if (error) {
    return (
      <Result
        status="error"
        title="加载失败"
        subTitle={error}
        extra={
          <Button onClick={() => navigate('/parse-jobs')}>返回列表</Button>
        }
      />
    )
  }

  if (!job) {
    return (
      <Result
        status="warning"
        title="未找到任务"
        extra={
          <Button onClick={() => navigate('/parse-jobs')}>返回列表</Button>
        }
      />
    )
  }

  // 解析失败:result.error 且无字段
  const failedNoFields =
    job.status === 'failed' &&
    (!job.result || !job.result.fields || Object.keys(job.result.fields).length === 0)

  if (failedNoFields) {
    return (
      <Result
        status="error"
        title="解析失败"
        subTitle={job.result?.error ?? '未知错误'}
        extra={
          <Space>
            <Button onClick={() => navigate('/parse-jobs')}>返回列表</Button>
            <Button
              type="primary"
              onClick={async () => {
                try {
                  const rerun = await parseJobApi.run(job.id)
                  setJob(rerun)
                  if (rerun.status === 'failed') {
                    message.error(rerun.result?.error ?? '重新解析仍失败')
                  }
                } catch (e: unknown) {
                  const msg = e instanceof Error ? e.message : '重新解析失败'
                  message.error(msg)
                }
              }}
            >
              重新解析
            </Button>
          </Space>
        }
      />
    )
  }

  const statusMeta = STATUS_META[job.status] ?? {
    color: 'default',
    text: job.status,
  }

  return (
    <Layout style={{ height: '100vh' }}>
      <Header
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          background: '#fff',
          padding: '0 16px',
          borderBottom: '1px solid #f0f0f0',
          flex: '0 0 64px',
        }}
      >
        <Space>
          <Button onClick={() => navigate('/parse-jobs')}>返回</Button>
          <Title level={4} style={{ margin: 0 }}>
            {job.drawing_name || `任务 ${job.id}`}
          </Title>
          <Tag color={statusMeta.color}>{statusMeta.text}</Tag>
          {job.template && (
            <Text type="secondary">模板:{job.template.name}</Text>
          )}
        </Space>
        {job.status === 'done' && (
          <Button onClick={() => setHistoryModalOpen(true)}>查看历史快照</Button>
        )}
      </Header>
      <Content style={{ padding: 12, overflow: 'hidden' }}>
        <div
          style={{
            display: 'flex',
            gap: 12,
            height: '100%',
            minHeight: 0,
          }}
        >
          <div
            style={{
              flex: '1 1 55%',
              minWidth: 0,
              border: '1px solid #f0f0f0',
              borderRadius: 4,
              overflow: 'hidden',
              background: '#fafafa',
            }}
          >
            <DrawingViewer jobId={job.id} />
          </div>
          <div
            style={{
              flex: '1 1 45%',
              minWidth: 0,
              border: '1px solid #f0f0f0',
              borderRadius: 4,
              overflow: 'auto',
              background: '#fff',
            }}
          >
            <ReviewPanel job={job} onChanged={setJob} history={history} />
          </div>
        </div>
      </Content>

      <Modal
        title="历史快照"
        open={historyModalOpen}
        onCancel={() => setHistoryModalOpen(false)}
        footer={<Button onClick={() => setHistoryModalOpen(false)}>关闭</Button>}
      >
        {history ? (
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item label="输出时间">
              {formatTime(history.created_at)}
            </Descriptions.Item>
            <Descriptions.Item label="快照 ID">
              {history.id}
            </Descriptions.Item>
            <Descriptions.Item label="output_oid">
              {history.output_oid ?? '—'}
            </Descriptions.Item>
            <Descriptions.Item label="涉及字段数">
              {getAiFieldCount(history)}
            </Descriptions.Item>
            <Descriptions.Item label="手动修改数">
              {getManualEditCount(history)}
            </Descriptions.Item>
            <Descriptions.Item label="图纸 OID">
              {history.drawing_oid}
            </Descriptions.Item>
          </Descriptions>
        ) : (
          <Text type="secondary">快照加载中或暂无快照。</Text>
        )}
      </Modal>
    </Layout>
  )
}
