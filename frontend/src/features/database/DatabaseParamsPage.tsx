import { useState, useEffect, useCallback } from 'react'
import {
  Layout,
  Typography,
  Button,
  Space,
  Table,
  Modal,
  Form,
  Input,
  Switch,
  Tag,
  Popconfirm,
  message,
  Upload,
  Tooltip,
  Row,
  Col,
  Card,
  Statistic,
  Input as SearchInput,
} from 'antd'
import type { UploadProps } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import {
  PlusOutlined,
  DeleteOutlined,
  EditOutlined,
  ArrowLeftOutlined,
  DownloadOutlined,
  UploadOutlined,
  DatabaseOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/store/auth'
import { databaseParamApi } from '@/lib/api/settings'
import type { DatabaseParamOut, DatabaseParamCreate } from '@/types'

const { Header, Content } = Layout
const { Title, Text } = Typography

export default function DatabaseParamsPage() {
  const navigate = useNavigate()
  const user = useAuth((s) => s.user)
  const logout = useAuth((s) => s.logout)
  const isAdmin = user?.role === 'admin'

  const [params, setParams] = useState<DatabaseParamOut[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<DatabaseParamOut | null>(null)
  const [searchText, setSearchText] = useState('')
  const [importLoading, setImportLoading] = useState(false)
  const [form] = Form.useForm()

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await databaseParamApi.list()
      setParams(data)
    } catch {
      message.error('加载数据库参数失败')
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
    form.setFieldsValue({ enabled: true })
    setModalOpen(true)
  }

  const handleEdit = (record: DatabaseParamOut) => {
    setEditing(record)
    form.setFieldsValue(record)
    setModalOpen(true)
  }

  const handleDelete = async (id: string) => {
    try {
      await databaseParamApi.delete(id)
      message.success('删除成功')
      load()
    } catch {
      message.error('删除失败')
    }
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      if (editing) {
        await databaseParamApi.update(editing.id, values)
        message.success('更新成功')
      } else {
        await databaseParamApi.create(values as DatabaseParamCreate)
        message.success('创建成功')
      }
      setModalOpen(false)
      load()
    } catch {
      // 校验失败
    }
  }

  const handleExport = async () => {
    try {
      await databaseParamApi.exportExcel()
      message.success('导出成功')
    } catch {
      message.error('导出失败')
    }
  }

  const handleImport: UploadProps['beforeUpload'] = async (file) => {
    setImportLoading(true)
    try {
      const result = await databaseParamApi.importExcel(file)
      message.success(`导入完成: 成功 ${result.imported} 条, 跳过 ${result.skipped} 条`)
      load()
    } catch {
      message.error('导入失败,请检查文件格式')
    } finally {
      setImportLoading(false)
    }
    // 阻止 antd 自动上传
    return false
  }

  // 过滤
  const filteredParams = searchText
    ? params.filter((p) => {
        const s = searchText.toLowerCase()
        return (
          p.category.toLowerCase().includes(s) ||
          p.model.toLowerCase().includes(s) ||
          p.field.toLowerCase().includes(s) ||
          p.value.toLowerCase().includes(s)
        )
      })
    : params

  // 统计分类数
  const categories = new Set(params.map((p) => p.category))

  const columns: ColumnsType<DatabaseParamOut> = [
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      width: 120,
      render: (v: string) => <Tag color="geekblue">{v}</Tag>,
      filters: Array.from(categories).map((c) => ({ text: c, value: c })),
      onFilter: (value, record) => record.category === String(value),
    },
    {
      title: '型号',
      dataIndex: 'model',
      key: 'model',
      width: 140,
    },
    {
      title: '字段',
      dataIndex: 'field',
      key: 'field',
      width: 140,
    },
    {
      title: '值',
      dataIndex: 'value',
      key: 'value',
    },
    {
      title: '单位',
      dataIndex: 'unit',
      key: 'unit',
      width: 80,
      render: (v: string | null) => v ?? '-',
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      key: 'enabled',
      width: 80,
      render: (v: boolean) => (v ? <Tag color="green">启用</Tag> : <Tag>禁用</Tag>),
    },
    {
      title: '版本',
      dataIndex: 'version',
      key: 'version',
      width: 70,
    },
    {
      title: '操作',
      key: 'action',
      width: 160,
      render: (_: unknown, record: DatabaseParamOut) =>
        isAdmin && (
          <Space>
            <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)}>
              编辑
            </Button>
            <Popconfirm title="确定删除?" onConfirm={() => handleDelete(record.id)}>
              <Button size="small" danger icon={<DeleteOutlined />} />
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
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/workspace')}>
            返回
          </Button>
          <Title level={4} style={{ margin: 0 }}>
            <DatabaseOutlined /> 数据库参数
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
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Card size="small">
              <Statistic title="参数总数" value={params.length} prefix={<DatabaseOutlined />} />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic title="分类数" value={categories.size} />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title="启用参数"
                value={params.filter((p) => p.enabled).length}
                valueStyle={{ color: '#3f8600' }}
              />
            </Card>
          </Col>
        </Row>

        <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Space>
            <SearchInput.Search
              placeholder="搜索分类/型号/字段/值"
              allowClear
              onSearch={setSearchText}
              style={{ width: 300 }}
            />
          </Space>
          <Space>
            {isAdmin && (
              <>
                <Tooltip title="从 Excel 导入（覆盖同名参数）">
                  <Upload
                    beforeUpload={handleImport}
                    showUploadList={false}
                    accept=".xlsx,.xls"
                  >
                    <Button icon={<UploadOutlined />} loading={importLoading}>
                      导入 Excel
                    </Button>
                  </Upload>
                </Tooltip>
                <Button icon={<DownloadOutlined />} onClick={handleExport}>
                  导出 Excel
                </Button>
                <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
                  添加参数
                </Button>
              </>
            )}
          </Space>
        </div>

        <Table
          columns={columns}
          dataSource={filteredParams}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 20, showSizeChanger: true }}
        />

        <Modal
          title={editing ? '编辑数据库参数' : '添加数据库参数'}
          open={modalOpen}
          onOk={handleSubmit}
          onCancel={() => setModalOpen(false)}
          width={500}
          okText="保存"
          cancelText="取消"
        >
          <Form form={form} layout="vertical">
            <Form.Item label="分类" name="category" rules={[{ required: true, message: '请输入分类' }]}>
              <Input placeholder="如 端子、连接器、线材" />
            </Form.Item>
            <Form.Item label="型号" name="model" rules={[{ required: true, message: '请输入型号' }]}>
              <Input placeholder="如 H-XQ-001" />
            </Form.Item>
            <Form.Item label="字段" name="field" rules={[{ required: true, message: '请输入字段' }]}>
              <Input placeholder="如 额定电流、接触电阻" />
            </Form.Item>
            <Form.Item label="值" name="value" rules={[{ required: true, message: '请输入值' }]}>
              <Input placeholder="如 10A" />
            </Form.Item>
            <Form.Item label="单位" name="unit">
              <Input placeholder="如 A、Ω、mm" />
            </Form.Item>
            <Form.Item label="启用" name="enabled">
              <Switch checkedChildren="是" unCheckedChildren="否" />
            </Form.Item>
          </Form>
        </Modal>
      </Content>
    </Layout>
  )
}
