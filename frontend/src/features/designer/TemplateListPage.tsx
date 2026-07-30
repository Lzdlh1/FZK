import { useCallback, useEffect, useState } from 'react'
import {
  Layout,
  Table,
  Button,
  Space,
  Typography,
  Popconfirm,
  message,
  Tag,
} from 'antd'
import { useNavigate } from 'react-router-dom'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'
import {
  PlusOutlined,
  EditOutlined,
  CopyOutlined,
  DeleteOutlined,
} from '@ant-design/icons'
import { templateApi } from '@/lib/api/templates'
import type { TemplateListItem } from '@/types'

const { Header, Content } = Layout
const { Title } = Typography

export default function TemplateListPage() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<TemplateListItem[]>([])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const list = await templateApi.list()
      setData(list)
    } catch (e: unknown) {
      message.error(e instanceof Error ? e.message : '加载模板列表失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const handleCopy = async (id: string) => {
    try {
      const t = await templateApi.get(id)
      navigate('/designer', {
        state: {
          snapshot: t.univer_snapshot,
          name: `${t.name} 副本`,
        },
      })
    } catch (e: unknown) {
      message.error(e instanceof Error ? e.message : '加载模板快照失败')
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await templateApi.remove(id)
      message.success('已删除')
      load()
    } catch (e: unknown) {
      message.error(e instanceof Error ? e.message : '删除失败')
    }
  }

  const columns: ColumnsType<TemplateListItem> = [
    {
      title: '模板名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string) => name || '(未命名)',
    },
    {
      title: '版本',
      dataIndex: 'version',
      key: 'version',
      width: 100,
      render: (v: number) => <Tag color="blue">v{v}</Tag>,
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 180,
      render: (t?: string) => (t ? dayjs(t).format('YYYY-MM-DD HH:mm') : '—'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 240,
      render: (_, r) => (
        <Space>
          <Button
            size="small"
            type="link"
            icon={<EditOutlined />}
            onClick={() => navigate(`/designer/${r.id}`)}
          >
            编辑
          </Button>
          <Button
            size="small"
            type="link"
            icon={<CopyOutlined />}
            onClick={() => handleCopy(r.id)}
          >
            复制
          </Button>
          <Popconfirm
            title="确认删除该模板?"
            description="删除后不可恢复"
            onConfirm={() => handleDelete(r.id)}
            okText="删除"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Button size="small" type="link" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
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
          模板列表
        </Title>
        <Space>
          <Button onClick={() => navigate('/workspace')}>返回工作台</Button>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => navigate('/designer')}
          >
            新建模板
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
