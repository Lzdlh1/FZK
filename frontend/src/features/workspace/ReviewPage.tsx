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
} from 'antd'
import { useNavigate, useParams } from 'react-router-dom'
import { parseJobApi } from '@/lib/api/parseJobs'
import type { ParseJobOut, ParseJobStatus } from '@/types'
import DrawingViewer from './DrawingViewer'
import ReviewPanel from './ReviewPanel'

const { Header, Content } = Layout
const { Title, Text } = Typography

const STATUS_META: Record<ParseJobStatus, { color: string; text: string }> = {
  pending: { color: 'default', text: '待解析' },
  parsing: { color: 'processing', text: '解析中' },
  review: { color: 'warning', text: '待审核' },
  done: { color: 'success', text: '已保存' },
  failed: { color: 'error', text: '失败' },
}

export default function ReviewPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [job, setJob] = useState<ParseJobOut | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    setLoading(true)
    setError(null)
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
            <ReviewPanel job={job} onChanged={setJob} />
          </div>
        </div>
      </Content>
    </Layout>
  )
}
