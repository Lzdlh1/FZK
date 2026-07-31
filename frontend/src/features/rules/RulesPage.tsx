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
  Select,
  Switch,
  InputNumber,
  Tag,
  Popconfirm,
  message,
  Tooltip,
  Row,
  Col,
  Card,
  Statistic,
  Divider,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import {
  PlusOutlined,
  DeleteOutlined,
  EditOutlined,
  ArrowLeftOutlined,
  BookOutlined,
  EyeOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/store/auth'
import { ruleApi } from '@/lib/api/rules'
import type { RuleOut, RuleCreate } from '@/types'

const { Header, Content } = Layout
const { Title, Text, Paragraph } = Typography
const { TextArea } = Input

/** 规则分类预设 */
const CATEGORIES = [
  { label: '通用', value: '通用', color: 'default' },
  { label: '图纸识别', value: '图纸识别', color: 'blue' },
  { label: '数据处理', value: '数据处理', color: 'green' },
  { label: '图示标注', value: '图示标注', color: 'orange' },
  { label: '单位换算', value: '单位换算', color: 'purple' },
  { label: '自定义', value: '自定义', color: 'cyan' },
]

/** 作用域预设 */
const SCOPES = [
  { label: '全局 (所有图纸)', value: 'global' },
  { label: '线束图纸', value: 'drawing_type:harness' },
  { label: '原理图', value: 'drawing_type:schematic' },
  { label: '接线图', value: 'drawing_type:wiring' },
  { label: '定制 (手动输入)', value: '' },
]

/** 示例规则模板 */
const RULE_TEMPLATES = [
  {
    name: '线束长度识别规则',
    category: '图纸识别',
    content: `识别线束图纸中的线束长度参数时，遵循以下规则：
1. 线束长度通常标注在尺寸线上，单位为毫米(mm)
2. 若标注为 "L=500"，则提取数值 500，单位 mm
3. 若标注为 "长度: 50cm"，需换算为 500mm
4. 尺寸线两端的箭头指向线束的起止点
5. 若有多段线束，分别提取各段长度并标注序号`,
  },
  {
    name: '端子型号提取规则',
    category: '数据处理',
    content: `从图纸表格或标注中提取端子型号时：
1. 端子型号通常由字母+数字组成，如 H-XQ-001、DJ7021-1.5-11
2. 优先从 BOM 表格中提取，其次从图纸标注中识别
3. 若型号旁边有括号注释，提取为备注
4. 同一图纸中可能出现公端子和母端子，需分别标注性别
5. 端子数量需与图纸标注的数量一致`,
  },
  {
    name: '图示标注区域定位',
    category: '图示标注',
    content: `定位图示中的标注区域时：
1. 标题栏位于图纸右下角，包含图号、名称、比例等信息
2. BOM 表格通常位于标题栏上方或图纸右侧
3. 技术要求文字通常位于图纸左下角或左上角
4. 尺寸标注沿线束走向，箭头垂直于线束方向
5. 剖面图和局部放大图有字母标识(A-A、B-B 等)，需关联主视图位置`,
  },
  {
    name: '单位统一换算规则',
    category: '单位换算',
    content: `所有提取的数值参数统一换算为国际标准单位：
1. 长度: 统一为毫米(mm)，1cm=10mm，1m=1000mm
2. 电流: 统一为安培(A)，1mA=0.001A
3. 电压: 统一为伏特(V)
4. 电阻: 统一为欧姆(Ω)，1kΩ=1000Ω
5. 截面积: 统一为平方毫米(mm²)，1AWG 需查表换算`,
  },
]

export default function RulesPage() {
  const navigate = useNavigate()
  const user = useAuth((s) => s.user)
  const logout = useAuth((s) => s.logout)
  const isAdmin = user?.role === 'admin'

  const [rules, setRules] = useState<RuleOut[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [viewModalOpen, setViewModalOpen] = useState(false)
  const [viewing, setViewing] = useState<RuleOut | null>(null)
  const [editing, setEditing] = useState<RuleOut | null>(null)
  const [filterCategory, setFilterCategory] = useState<string | undefined>()
  const [form] = Form.useForm()

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await ruleApi.list({ category: filterCategory })
      setRules(data)
    } catch {
      message.error('加载规则列表失败')
    } finally {
      setLoading(false)
    }
  }, [filterCategory])

  useEffect(() => {
    load()
  }, [load])

  const handleAdd = () => {
    setEditing(null)
    form.resetFields()
    form.setFieldsValue({
      category: '通用',
      scope: 'global',
      enabled: true,
      sort_order: 0,
    })
    setModalOpen(true)
  }

  const handleEdit = (record: RuleOut) => {
    setEditing(record)
    form.setFieldsValue(record)
    setModalOpen(true)
  }

  const handleDelete = async (id: string) => {
    try {
      await ruleApi.delete(id)
      message.success('删除成功')
      load()
    } catch {
      message.error('删除失败')
    }
  }

  const handleView = (record: RuleOut) => {
    setViewing(record)
    setViewModalOpen(true)
  }

  const handleCopyTemplate = (template: (typeof RULE_TEMPLATES)[0]) => {
    setEditing(null)
    form.setFieldsValue({
      name: template.name,
      category: template.category,
      content: template.content,
      scope: 'global',
      enabled: true,
      sort_order: 0,
    })
    setModalOpen(true)
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      if (editing) {
        await ruleApi.update(editing.id, values)
        message.success('更新成功')
      } else {
        await ruleApi.create(values as RuleCreate)
        message.success('创建成功')
      }
      setModalOpen(false)
      load()
    } catch {
      // 校验失败
    }
  }

  const columns: ColumnsType<RuleOut> = [
    {
      title: '排序',
      dataIndex: 'sort_order',
      key: 'sort_order',
      width: 60,
    },
    {
      title: '规则名称',
      dataIndex: 'name',
      key: 'name',
      width: 200,
      render: (name: string) => <Text strong>{name}</Text>,
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      width: 110,
      render: (cat: string) => {
        const c = CATEGORIES.find((x) => x.value === cat)
        return <Tag color={c?.color ?? 'default'}>{cat}</Tag>
      },
      filters: CATEGORIES.map((c) => ({ text: c.label, value: c.value })),
      onFilter: (value, record) => record.category === String(value),
    },
    {
      title: '作用域',
      dataIndex: 'scope',
      key: 'scope',
      width: 130,
      render: (scope: string | null) => {
        if (!scope || scope === 'global') return <Tag>全局</Tag>
        const s = SCOPES.find((x) => x.value === scope)
        return <Tag color="geekblue">{s?.label ?? scope}</Tag>
      },
    },
    {
      title: '内容预览',
      dataIndex: 'content',
      key: 'content',
      ellipsis: true,
      render: (content: string) => (
        <Text type="secondary" ellipsis={{ tooltip: content }} style={{ maxWidth: 300 }}>
          {content}
        </Text>
      ),
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      key: 'enabled',
      width: 80,
      render: (v: boolean) => (v ? <Tag color="green">启用</Tag> : <Tag>禁用</Tag>),
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 160,
      render: (v: string) => new Date(v).toLocaleString('zh-CN'),
    },
    {
      title: '操作',
      key: 'action',
      width: 180,
      render: (_: unknown, record: RuleOut) => (
        <Space>
          <Tooltip title="查看全文">
            <Button size="small" icon={<EyeOutlined />} onClick={() => handleView(record)} />
          </Tooltip>
          {isAdmin && (
            <>
              <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)}>
                编辑
              </Button>
              <Popconfirm title="确定删除该规则?" onConfirm={() => handleDelete(record.id)}>
                <Button size="small" danger icon={<DeleteOutlined />} />
              </Popconfirm>
            </>
          )}
        </Space>
      ),
    },
  ]

  const enabledCount = rules.filter((r) => r.enabled).length
  const categoryCount = new Set(rules.map((r) => r.category)).size

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
            <BookOutlined /> AI 规则管理
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
              <Statistic title="规则总数" value={rules.length} prefix={<BookOutlined />} />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic title="启用规则" value={enabledCount} valueStyle={{ color: '#3f8600' }} />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic title="分类数" value={categoryCount} />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic title="禁用规则" value={rules.length - enabledCount} valueStyle={{ color: '#cf1322' }} />
            </Card>
          </Col>
        </Row>

        {/* 规则模板快捷区 */}
        {isAdmin && (
          <Card size="small" title="规则模板（点击快速创建）" style={{ marginBottom: 16 }}>
            <Row gutter={[12, 12]}>
              {RULE_TEMPLATES.map((tpl) => (
                <Col key={tpl.name} xs={24} sm={12} md={6}>
                  <Card
                    size="small"
                    hoverable
                    onClick={() => handleCopyTemplate(tpl)}
                    style={{ height: '100%' }}
                  >
                    <Space direction="vertical" size={4} style={{ width: '100%' }}>
                      <Space>
                        <Tag color={CATEGORIES.find((c) => c.value === tpl.category)?.color}>
                          {tpl.category}
                        </Tag>
                        <Text strong>{tpl.name}</Text>
                      </Space>
                      <Text type="secondary" ellipsis style={{ fontSize: 12 }}>
                        {tpl.content.split('\n')[0]}
                      </Text>
                    </Space>
                  </Card>
                </Col>
              ))}
            </Row>
          </Card>
        )}

        <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Select
            allowClear
            placeholder="按分类筛选"
            style={{ width: 200 }}
            value={filterCategory}
            onChange={setFilterCategory}
            options={CATEGORIES.map((c) => ({ label: c.label, value: c.value }))}
          />
          {isAdmin && (
            <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
              添加规则
            </Button>
          )}
        </div>

        <Table
          columns={columns}
          dataSource={rules}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 20, showSizeChanger: true }}
        />

        {/* 新增/编辑 Modal */}
        <Modal
          title={editing ? '编辑规则' : '添加规则'}
          open={modalOpen}
          onOk={handleSubmit}
          onCancel={() => setModalOpen(false)}
          width={700}
          okText="保存"
          cancelText="取消"
        >
          <Form form={form} layout="vertical">
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item label="规则名称" name="name" rules={[{ required: true, message: '请输入规则名称' }]}>
                  <Input placeholder="如 线束长度识别规则" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item label="分类" name="category" rules={[{ required: true }]}>
                  <Select
                    showSearch
                    options={CATEGORIES.map((c) => ({ label: c.label, value: c.value }))}
                  />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item label="作用域" name="scope">
                  <Select
                    showSearch
                    allowClear
                    placeholder="选择作用域"
                    options={SCOPES.filter((s) => s.value).map((s) => ({ label: s.label, value: s.value }))}
                  />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item label="排序(越小越靠前)" name="sort_order">
                  <InputNumber min={0} max={9999} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item label="启用" name="enabled">
                  <Switch checkedChildren="是" unCheckedChildren="否" />
                </Form.Item>
              </Col>
            </Row>
            <Form.Item
              label="规则内容"
              name="content"
              rules={[{ required: true, message: '请输入规则内容' }]}
              extra="教 AI 如何识别和处理图纸数据与图示的指令，支持多行文本"
            >
              <TextArea
                rows={10}
                placeholder={`输入规则内容，例如：
1. 线束长度标注在尺寸线上，单位 mm
2. 端子型号格式为 字母+数字
3. 标题栏位于图纸右下角`}
                showCount
                maxLength={5000}
              />
            </Form.Item>
          </Form>
        </Modal>

        {/* 查看全文 Modal */}
        <Modal
          title={viewing?.name}
          open={viewModalOpen}
          onCancel={() => setViewModalOpen(false)}
          footer={[
            <Button key="close" onClick={() => setViewModalOpen(false)}>
              关闭
            </Button>,
            ...(isAdmin
              ? [
                  <Button
                    key="edit"
                    type="primary"
                    icon={<EditOutlined />}
                    onClick={() => {
                      setViewModalOpen(false)
                      if (viewing) handleEdit(viewing)
                    }}
                  >
                    编辑
                  </Button>,
                ]
              : []),
          ]}
          width={700}
        >
          {viewing && (
            <div>
              <Space style={{ marginBottom: 12 }}>
                <Tag color={CATEGORIES.find((c) => c.value === viewing.category)?.color}>
                  {viewing.category}
                </Tag>
                {viewing.scope && viewing.scope !== 'global' && (
                  <Tag color="geekblue">
                    {SCOPES.find((s) => s.value === viewing.scope)?.label ?? viewing.scope}
                  </Tag>
                )}
                <Tag color={viewing.enabled ? 'green' : 'default'}>
                  {viewing.enabled ? '启用' : '禁用'}
                </Tag>
              </Space>
              <Divider style={{ margin: '8px 0' }} />
              <Paragraph
                style={{
                  whiteSpace: 'pre-wrap',
                  background: '#fafafa',
                  padding: 16,
                  borderRadius: 8,
                  fontFamily: 'monospace',
                  maxHeight: 400,
                  overflowY: 'auto',
                }}
              >
                {viewing.content}
              </Paragraph>
            </div>
          )}
        </Modal>
      </Content>
    </Layout>
  )
}
