import { useState, useEffect, useCallback } from 'react'
import {
  Layout,
  Tabs,
  Typography,
  Button,
  Space,
  Table,
  Modal,
  Form,
  Input,
  InputNumber,
  Switch,
  Tag,
  Popconfirm,
  message,
  Select,
  Tooltip,
  Row,
  Col,
  Card,
  Statistic,
} from 'antd'
import { useNavigate } from 'react-router-dom'
import {
  PlusOutlined,
  DeleteOutlined,
  EditOutlined,
  ArrowLeftOutlined,
  ApiOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import { useAuth } from '@/store/auth'
import { aiProviderApi } from '@/lib/api/settings'
import type {
  AIProviderOut,
  AIProviderCreate,
} from '@/types'

const { Header, Content } = Layout
const { Title, Text } = Typography

/* 常见 AI 供应商预设 */
const PROVIDER_PRESETS = [
  {
    name: 'OpenAI',
    endpoint: 'https://api.openai.com/v1/chat/completions',
    models: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-4-vision-preview'],
  },
  {
    name: '智谱 GLM',
    endpoint: 'https://open.bigmodel.cn/api/paas/v4/chat/completions',
    models: ['glm-4v', 'glm-4v-plus', 'glm-4-plus'],
  },
  {
    name: '通义千问',
    endpoint: 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions',
    models: ['qwen-vl-max', 'qwen-vl-plus', 'qwen-vl-72b-instruct'],
  },
  {
    name: '百度文心',
    endpoint: 'https://qianfan.baidubce.com/v2/chat/completions',
    models: ['ernie-4.0-8k', 'ernie-vil-turbo-v1'],
  },
  {
    name: '自定义',
    endpoint: '',
    models: [],
  },
]

export default function SettingsPage() {
  const navigate = useNavigate()
  const user = useAuth((s) => s.user)
  const logout = useAuth((s) => s.logout)
  const isAdmin = user?.role === 'admin'

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
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/workspace')}>
            返回
          </Button>
          <Title level={4} style={{ margin: 0 }}>
            系统设置
          </Title>
        </Space>
        <Space>
          <Text>当前用户:{user?.name ?? '未知'}</Text>
          <Button
            onClick={() => {
              logout()
              navigate('/login')
            }}
          >
            登出
          </Button>
        </Space>
      </Header>
      <Content style={{ padding: 24 }}>
        <Tabs
          defaultActiveKey="ai"
          items={[
            {
              key: 'ai',
              label: (
                <span>
                  <ApiOutlined /> AI 供应商配置
                </span>
              ),
              children: <AIProviderTab isAdmin={isAdmin} />,
            },
            {
              key: 'about',
              label: '关于系统',
              children: <AboutTab />,
            },
          ]}
        />
      </Content>
    </Layout>
  )
}

/* ===================== AI 供应商 Tab ===================== */

function AIProviderTab({ isAdmin }: { isAdmin: boolean }) {
  const [providers, setProviders] = useState<AIProviderOut[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<AIProviderOut | null>(null)
  const [healthLoading, setHealthLoading] = useState<string | null>(null)
  const [testing, setTesting] = useState(false)
  const [form] = Form.useForm()

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await aiProviderApi.list()
      setProviders(data)
    } catch {
      message.error('加载 AI 供应商列表失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const handleAdd = () => {
    setEditing(null)
    form.resetFields()
    form.setFieldsValue({ weight: 1, healthy: true, presetName: '自定义' })
    setModalOpen(true)
  }

  const handleEdit = (record: AIProviderOut) => {
    setEditing(record)
    form.setFieldsValue({
      ...record,
      api_key: '',
      presetName: '自定义',
    })
    setModalOpen(true)
  }

  const handleDelete = async (id: string) => {
    try {
      await aiProviderApi.delete(id)
      message.success('删除成功')
      load()
    } catch {
      message.error('删除失败')
    }
  }

  const handleHealthCheck = async (id: string) => {
    setHealthLoading(id)
    try {
      const result = await aiProviderApi.checkHealth(id)
      if (result.healthy) {
        message.success(`${result.name} 健康检查通过`)
      } else {
        message.error(`${result.name} 健康检查失败: ${result.error ?? '未知错误'}`)
      }
      load()
    } catch {
      message.error('健康检查请求失败')
    } finally {
      setHealthLoading(null)
    }
  }

  // 用当前表单配置(未保存)直接测试连通性,便于保存前验证中转站等配置
  const handleTestConnection = async () => {
    try {
      const values = await form.validateFields(['endpoint', 'api_key', 'model'])
      setTesting(true)
      const result = await aiProviderApi.testConnection({
        name: values.name,
        endpoint: values.endpoint,
        api_key: values.api_key || '',
        model: values.model,
      })
      if (result.healthy) {
        message.success(
          `连通性测试通过${result.latency_ms != null ? `(延迟 ${result.latency_ms}ms)` : ''}`
        )
      } else {
        message.error(`连通性测试失败: ${result.error ?? '未知错误'}`)
      }
    } catch (e: unknown) {
      // 表单校验失败或请求异常
      if (e instanceof Error && e.message) {
        message.error(`连通性测试失败: ${e.message}`)
      } else if (
        e &&
        typeof e === 'object' &&
        'errorFields' in e
      ) {
        message.warning('请先填写端点、API Key、模型')
      } else {
        message.error('连通性测试请求失败')
      }
    } finally {
      setTesting(false)
    }
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      const { presetName, ...rest } = values
      if (editing) {
        const updateData: Record<string, unknown> = { ...rest }
        if (!updateData.api_key) delete updateData.api_key
        await aiProviderApi.update(editing.id, updateData as never)
        message.success('更新成功')
      } else {
        await aiProviderApi.create(rest as AIProviderCreate)
        message.success('创建成功')
      }
      setModalOpen(false)
      load()
    } catch {
      // 校验失败
    }
  }

  const handlePresetChange = (presetName: string) => {
    const preset = PROVIDER_PRESETS.find((p) => p.name === presetName)
    if (preset) {
      form.setFieldsValue({
        name: preset.name === '自定义' ? '' : preset.name,
        endpoint: preset.endpoint,
        model: preset.models[0] ?? '',
      })
    }
  }

  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      width: 120,
    },
    {
      title: '端点',
      dataIndex: 'endpoint',
      key: 'endpoint',
      ellipsis: true,
    },
    {
      title: '模型',
      dataIndex: 'model',
      key: 'model',
      width: 180,
      render: (model: string) => <Tag color="blue">{model}</Tag>,
    },
    {
      title: '权重',
      dataIndex: 'weight',
      key: 'weight',
      width: 80,
    },
    {
      title: '状态',
      dataIndex: 'healthy',
      key: 'healthy',
      width: 100,
      render: (healthy: boolean) =>
        healthy ? (
          <Tag icon={<CheckCircleOutlined />} color="success">
            健康
          </Tag>
        ) : (
          <Tag icon={<CloseCircleOutlined />} color="error">
            异常
          </Tag>
        ),
    },
    {
      title: '最后检查',
      dataIndex: 'last_check_at',
      key: 'last_check_at',
      width: 180,
      render: (v: string | null) => (v ? new Date(v).toLocaleString('zh-CN') : '-'),
    },
    {
      title: '操作',
      key: 'action',
      width: 240,
      render: (_: unknown, record: AIProviderOut) => (
        <Space>
          <Tooltip title="健康检查">
            <Button
              size="small"
              icon={<ReloadOutlined />}
              loading={healthLoading === record.id}
              onClick={() => handleHealthCheck(record.id)}
            />
          </Tooltip>
          {isAdmin && (
            <>
              <Button
                size="small"
                icon={<EditOutlined />}
                onClick={() => handleEdit(record)}
              >
                编辑
              </Button>
              <Popconfirm
                title="确定删除该供应商?"
                onConfirm={() => handleDelete(record.id)}
              >
                <Button size="small" danger icon={<DeleteOutlined />} />
              </Popconfirm>
            </>
          )}
        </Space>
      ),
    },
  ]

  const currentPreset = Form.useWatch('presetName', form)
  const presetModels =
    PROVIDER_PRESETS.find((p) => p.name === currentPreset)?.models ?? []

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="供应商总数"
              value={providers.length}
              prefix={<ApiOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="健康供应商"
              value={providers.filter((p) => p.healthy).length}
              valueStyle={{ color: '#3f8600' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="异常供应商"
              value={providers.filter((p) => !p.healthy).length}
              valueStyle={{ color: '#cf1322' }}
              prefix={<CloseCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <div style={{ marginBottom: 16 }}>
        {isAdmin && (
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            添加 AI 供应商
          </Button>
        )}
      </div>

      <Table
        columns={columns}
        dataSource={providers}
        rowKey="id"
        loading={loading}
        pagination={false}
      />

      <Modal
        title={editing ? '编辑 AI 供应商' : '添加 AI 供应商'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        width={600}
        okText="保存"
        cancelText="取消"
        footer={[
          <Button key="cancel" onClick={() => setModalOpen(false)}>
            取消
          </Button>,
          <Button
            key="test"
            loading={testing}
            onClick={handleTestConnection}
            style={{ marginRight: 'auto' }}
          >
            测试连通性
          </Button>,
          <Button key="save" type="primary" onClick={handleSubmit}>
            保存
          </Button>,
        ]}
      >
        <Form form={form} layout="vertical">
          <Form.Item label="供应商预设" name="presetName">
            <Select
              placeholder="选择预设或自定义"
              onChange={handlePresetChange}
              options={PROVIDER_PRESETS.map((p) => ({ label: p.name, value: p.name }))}
            />
          </Form.Item>
          <Form.Item
            label="名称"
            name="name"
            rules={[{ required: true, message: '请输入供应商名称' }]}
          >
            <Input placeholder="如 OpenAI、智谱 GLM" />
          </Form.Item>
          <Form.Item
            label="API 端点"
            name="endpoint"
            rules={[{ required: true, message: '请输入 API 端点' }]}
          >
            <Input placeholder="https://api.openai.com/v1/chat/completions" />
          </Form.Item>
          <Form.Item
            label="模型"
            name="model"
            rules={[{ required: true, message: '请选择或输入模型' }]}
          >
            {presetModels.length > 0 ? (
              <Select
                placeholder="选择模型"
                showSearch
                allowClear
                options={presetModels.map((m) => ({ label: m, value: m }))}
              />
            ) : (
              <Input placeholder="输入模型名称" />
            )}
          </Form.Item>
          <Form.Item
            label="API Key"
            name="api_key"
            rules={editing ? [] : [{ required: true, message: '请输入 API Key' }]}
          >
            <Input.Password
              placeholder={editing ? '留空则不修改' : 'sk-...'}
            />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="权重(越大越优先)" name="weight">
                <InputNumber min={1} max={100} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="启用" name="healthy">
                <Switch checkedChildren="是" unCheckedChildren="否" />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>
    </div>
  )
}

/* ===================== 关于系统 Tab ===================== */

function AboutTab() {
  return (
    <Card>
      <Row gutter={[16, 16]}>
        <Col span={24}>
          <Title level={4}>线束工艺辅助卡系统</Title>
          <Text type="secondary">
            基于 AI 视觉识别的全栈线束工艺辅助卡生成系统，支持图纸上传、自动参数抽取、公式计算与 Excel 输出。
          </Text>
        </Col>
        <Col span={8}>
          <Card size="small" title="后端技术">
            <Text type="secondary">
              FastAPI + SQLAlchemy + Alembic
              {'\n'}SQLite / PostgreSQL
              {'\n'}MinIO / 本地存储
              {'\n'}OpenAI 兼容视觉模型
            </Text>
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small" title="前端技术">
            <Text type="secondary">
              React 18 + TypeScript
              {'\n'}Ant Design 5
              {'\n'}Univer 表格引擎
              {'\n'}Vite + Zustand
            </Text>
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small" title="部署方式">
            <Text type="secondary">
              Docker Compose
              {'\n'}Nginx 反向代理
              {'\n'}开发环境: SQLite
              {'\n'}生产环境: PostgreSQL + MinIO
            </Text>
          </Card>
        </Col>
      </Row>
    </Card>
  )
}
