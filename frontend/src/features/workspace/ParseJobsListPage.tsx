import { useCallback, useEffect, useState } from 'react'
import { Layout, Table, Button, Space, Tag, Typography, message } from 'antd'
import { useNavigate } from 'react-router-dom'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'
import { parseJobApi } from '@/lib/api/parseJobs'
import type { ParseJobListItem, ParseJobStatus } from '@/types'

const { Header, Content } = Layout
const { Title } = Typography

const STATUS_META: Record<ParseJobStatus, { color: string; text: string }> = {
  pending: { color: 'default', text: '待解析' },
  parsing: { color: 'processing', text: '解析中' },
  review: { color: 'warning', text: '待审核' },
  done: { color: 'success', text: '已保存' },
  failed: { color: 'error', text: '失败' },
}

export default function ParseJobsListPage() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<ParseJobListItem[]>([])
  const [rerunningId, setRerunningId] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const list = await parseJobApi.list()
      setData(list)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '加载任务列表失败'
      message.error(msg)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const handleRerun = async (id: string) => {
    setRerunningId(id)
    try {
      const job = await parseJobApi.run(id)
      if (job.status === 'failed') {
        message.error('解析失败:' + (job.result?.error ?? '未知错误'))
      } else {
        message.success('解析完成')
        navigate(`/parse-jobs/${job.id}/review`)
        return
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '重新解析失败'
      message.error(msg)
    } finally {
      setRerunningId(null)
      load()
    }
  }

  const columns: ColumnsType<ParseJobListItem> = [
    {
      title: '任务名',
      dataIndex: 'drawing_name',
      key: 'drawing_name',
      render: (name: string) => name || '(未命名)',
    },
    {
      title: '模板',
      key: 'template',
      render: (_, r) => r.template?.name ?? r.template_id,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (s: ParseJobStatus) => (
        <Tag color={STATUS_META[s].color}>{STATUS_META[s].text}</Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (t: string) => (t ? dayjs(t).format('YYYY-MM-DD HH:mm') : '—'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      render: (_, r) => (
        <Space>
          {(r.status === 'review' || r.status === 'done') && (
            <Button
              size="small"
              type="link"
              onClick={() => navigate(`/parse-jobs/${r.id}/review`)}
            >
              查看 / 审核
            </Button>
          )}
          {(r.status === 'failed' || r.status === 'pending') && (
            <Button
              size="small"
              type="link"
              loading={rerunningId === r.id}
              onClick={() => handleRerun(r.id)}
            >
              重新解析
            </Button>
          )}
        </Space>
      ),
    },
  ]

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          background: '#fff',
          padding: '0 24px',
          borderBottom: '1px solid #f0f0f0',
        }}
      >
        <Title level={4} style={{ margin: 0 }}>
          解析任务列表
        </Title>
        <Space>
          <Button onClick={() => navigate('/workspace')}>返回工作台</Button>
          <Button type="primary" onClick={() => navigate('/workspace/new')}>
            新建任务
          </Button>
        </Space>
      </Header>
      <Content style={{ padding: 24 }}>
        <Table
          columns={columns}
          dataSource={data}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 20, showSizeChanger: false }}
        />
      </Content>
    </Layout>
  )
}
