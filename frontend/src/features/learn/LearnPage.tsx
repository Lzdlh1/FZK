import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Layout,
  Select,
  Upload,
  Button,
  Space,
  Typography,
  message,
  Input,
  Tag,
  Popconfirm,
  Spin,
  Empty,
  Alert,
  Divider,
} from 'antd'
import {
  ArrowLeftOutlined,
  SendOutlined,
  UploadOutlined,
  DeleteOutlined,
  SaveOutlined,
  RobotOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import dayjs from 'dayjs'
import { templateApi } from '@/lib/api/templates'
import { learnApi } from '@/lib/api/learn'
import type {
  FieldResult,
  LearnSampleOut,
  TemplateListItem,
} from '@/types'

const { Header, Content } = Layout
const { Title, Text, Paragraph } = Typography

/** 对话消息 */
interface ChatMsg {
  id: string
  role: 'user' | 'assistant' | 'system'
  text?: string
  imageUrl?: string
  imageOid?: string
  fields?: Record<string, FieldResult>
  /** 用户纠正后的字段值:name -> value */
  fieldsEdited?: Record<string, unknown>
  saved?: boolean
}

let msgSeq = 0
const nextId = () => `msg-${Date.now()}-${msgSeq++}`

const STATUS_TEXT: Record<string, string> = {
  extracted: '已识别',
  low_confidence: '低置信',
  not_found: '未找到',
  error: '错误',
  manual: '手动',
  formula: '公式',
}

const STATUS_COLOR: Record<string, string> = {
  extracted: 'default',
  low_confidence: 'warning',
  not_found: 'error',
  error: 'error',
}

/** AI 解析结果气泡:字段可编辑,纠正后可保存为训练样本 */
function FieldBubble({
  msg,
  templateId,
  onEdited,
  onSaved,
  saving,
}: {
  msg: ChatMsg
  templateId: string
  onEdited: (id: string, edited: Record<string, unknown>) => void
  onSaved: (id: string) => void
  saving: boolean
}) {
  const fields = msg.fields ?? {}
  const edited = msg.fieldsEdited ?? {}

  const handleSave = async () => {
    if (!templateId || !msg.imageOid) return
    // 构造期望结果:优先用户纠正值,无纠正用 AI 原值
    const expectedFields: Record<string, unknown> = {}
    for (const [name, field] of Object.entries(fields)) {
      const value =
        name in edited
          ? edited[name]
          : (field as FieldResult).value
      expectedFields[name] = { value: value ?? null }
    }
    try {
      await learnApi.createSample({
        template_id: templateId,
        image_oid: msg.imageOid,
        expected_json: { fields: expectedFields },
      })
      message.success('已保存为训练样本,后续解析该模板将参考此示例')
      onSaved(msg.id)
    } catch (e: unknown) {
      message.error(e instanceof Error ? e.message : '保存样本失败')
    }
  }

  return (
    <div style={{ maxWidth: 560 }}>
      <div style={{ marginBottom: 8, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {Object.entries(fields).map(([name, field]) => {
          const f = field as FieldResult
          const value =
            name in edited ? edited[name] : f.value
          const conf = f.confidence
          return (
            <div
              key={name}
              style={{
                border: '1px solid #f0f0f0',
                borderRadius: 6,
                padding: '6px 10px',
                background: '#fff',
                width: 250,
              }}
            >
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: 4,
                }}
              >
                <Text strong style={{ fontSize: 12 }}>
                  {name}
                </Text>
                <Space size={4}>
                  {conf != null && (
                    <Tag style={{ fontSize: 11, marginRight: 0 }}>
                      {(conf * 100).toFixed(0)}%
                    </Tag>
                  )}
                  {f.status && (
                    <Tag
                      color={STATUS_COLOR[f.status] ?? 'default'}
                      style={{ fontSize: 11, marginRight: 0 }}
                    >
                      {STATUS_TEXT[f.status] ?? f.status}
                    </Tag>
                  )}
                </Space>
              </div>
              <Input
                size="small"
                value={value == null ? '' : String(value)}
                onChange={(e) => {
                  const next = { ...edited, [name]: e.target.value }
                  onEdited(msg.id, next)
                }}
              />
            </div>
          )
        })}
      </div>
      <Button
        size="small"
        type="primary"
        icon={<SaveOutlined />}
        loading={saving}
        disabled={msg.saved}
        onClick={handleSave}
      >
        {msg.saved ? '已保存为训练样本' : '保存为训练样本'}
      </Button>
    </div>
  )
}

/** 训练样本面板 */
function SamplePanel({
  templateId,
  samples,
  loading,
  onReload,
}: {
  templateId: string
  samples: LearnSampleOut[]
  loading: boolean
  onReload: () => void
}) {
  const [imgs, setImgs] = useState<Record<string, string>>({})

  useEffect(() => {
    setImgs({})
    let cancelled = false
    if (!templateId) return
    samples.forEach((s) => {
      learnApi
        .loadSampleImage(s.id)
        .then((url) => {
          if (!cancelled) setImgs((prev) => ({ ...prev, [s.id]: url }))
        })
        .catch(() => undefined)
    })
    return () => {
      cancelled = true
    }
  }, [templateId, samples])

  const handleDelete = async (id: string) => {
    try {
      await learnApi.deleteSample(id)
      message.success('已删除样本')
      onReload()
    } catch (e: unknown) {
      message.error(e instanceof Error ? e.message : '删除失败')
    }
  }

  const extractSummary = (s: LearnSampleOut): string => {
    const fields = (s.expected_json as { fields?: Record<string, unknown> })
      ?.fields
    if (!fields) return ''
    return Object.entries(fields)
      .map(([name, v]) => {
        const val = (v as { value?: unknown })?.value
        return `${name}=${val ?? ''}`
      })
      .join(' · ')
  }

  if (loading) return <Spin style={{ display: 'block', margin: '24px auto' }} />
  if (samples.length === 0) {
    return <Empty description="暂无训练样本" image={Empty.PRESENTED_IMAGE_SIMPLE} />
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {samples.map((s) => (
        <div
          key={s.id}
          style={{
            border: '1px solid #f0f0f0',
            borderRadius: 6,
            padding: 8,
            background: '#fff',
          }}
        >
          <div style={{ display: 'flex', gap: 8 }}>
            {imgs[s.id] ? (
              <img
                src={imgs[s.id]}
                alt="样本图"
                style={{
                  width: 64,
                  height: 64,
                  objectFit: 'cover',
                  borderRadius: 4,
                  border: '1px solid #eee',
                }}
              />
            ) : (
              <div
                style={{
                  width: 64,
                  height: 64,
                  borderRadius: 4,
                  background: '#fafafa',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <RobotOutlined style={{ color: '#bbb' }} />
              </div>
            )}
            <div style={{ flex: 1, minWidth: 0 }}>
              <Text style={{ fontSize: 12 }} ellipsis>
                {extractSummary(s) || '(空结果)'}
              </Text>
              <div style={{ marginTop: 4 }}>
                <Text type="secondary" style={{ fontSize: 11 }}>
                  {dayjs(s.created_at).format('MM-DD HH:mm')}
                </Text>
              </div>
            </div>
            <Popconfirm
              title="删除该训练样本?"
              description="连同示例图纸一起删除,不可恢复。"
              onConfirm={() => handleDelete(s.id)}
              okText="删除"
              okButtonProps={{ danger: true }}
              cancelText="取消"
            >
              <Button size="small" type="text" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          </div>
        </div>
      ))}
    </div>
  )
}

export default function LearnPage() {
  const navigate = useNavigate()
  const [templates, setTemplates] = useState<TemplateListItem[]>([])
  const [templateId, setTemplateId] = useState<string>()
  const [msgs, setMsgs] = useState<ChatMsg[]>([])
  const [file, setFile] = useState<File | null>(null)
  const [sending, setSending] = useState(false)
  const [savingId, setSavingId] = useState<string | null>(null)
  const [samples, setSamples] = useState<LearnSampleOut[]>([])
  const [samplesLoading, setSamplesLoading] = useState(false)
  const listRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // 加载模板列表
  useEffect(() => {
    templateApi
      .list()
      .then(setTemplates)
      .catch(() => {
        message.error('加载模板列表失败')
      })
  }, [])

  // 模板变化:清空对话并重载样本
  useEffect(() => {
    setMsgs([])
    setFile(null)
    if (!templateId) {
      setSamples([])
      return
    }
    setSamplesLoading(true)
    learnApi
      .listSamples(templateId)
      .then(setSamples)
      .catch(() => {
        setSamples([])
        message.error('加载训练样本失败')
      })
      .finally(() => setSamplesLoading(false))
  }, [templateId])

  // 新消息自动滚到底部
  useEffect(() => {
    const el = listRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [msgs])

  const pushMsg = (m: ChatMsg) => setMsgs((prev) => [...prev, m])
  const updateMsg = (id: string, patch: Partial<ChatMsg>) =>
    setMsgs((prev) => prev.map((m) => (m.id === id ? { ...m, ...patch } : m)))

  const handleSend = async () => {
    if (!templateId) {
      message.warning('请先选择要训练的模板')
      return
    }
    if (!file) {
      message.warning('请先上传示例图纸')
      return
    }
    const imageUrl = URL.createObjectURL(file)
    const userMsg: ChatMsg = {
      id: nextId(),
      role: 'user',
      text: file.name,
      imageUrl,
    }
    const loadingId = nextId()
    pushMsg(userMsg)
    pushMsg({ id: loadingId, role: 'assistant', text: '正在尝试解析这张示例图纸…' })
    setSending(true)
    try {
      const res = await learnApi.tryParse(templateId, file)
      updateMsg(loadingId, {
        role: 'assistant',
        text: `已解析「${res.drawing_name}」。请检查下方字段,纠正错误后保存为训练样本;AI 后续解析会参考这些示例。`,
        imageOid: res.image_oid,
        fields: res.fields,
        fieldsEdited: {},
        saved: false,
      })
    } catch (e: unknown) {
      updateMsg(loadingId, {
        role: 'system',
        text: e instanceof Error ? e.message : '解析失败,请重试',
      })
    } finally {
      setSending(false)
      setFile(null)
    }
  }

  const handleEdited = (id: string, edited: Record<string, unknown>) =>
    updateMsg(id, { fieldsEdited: edited })

  const handleSaved = (id: string) => {
    updateMsg(id, { saved: true })
    if (templateId) {
      learnApi
        .listSamples(templateId)
        .then(setSamples)
        .catch(() => undefined)
    }
  }

  const reloadSamples = useCallback(() => {
    if (!templateId) return
    learnApi
      .listSamples(templateId)
      .then(setSamples)
      .catch(() => undefined)
  }, [templateId])

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
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/workspace')}>
            返回
          </Button>
          <Title level={4} style={{ margin: 0 }}>
            AI 学习
          </Title>
        </Space>
        <Space>
          <Text type="secondary">
            选择模板后,上传示例图纸让 AI 尝试解析,纠正结果并保存为训练样本
          </Text>
          <Select
            placeholder="选择训练模板"
            style={{ width: 240 }}
            value={templateId}
            onChange={setTemplateId}
            options={templates.map((t) => ({ label: t.name, value: t.id }))}
          />
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
          {/* 对话区 */}
          <div
            style={{
              flex: '1 1 auto',
              minWidth: 0,
              display: 'flex',
              flexDirection: 'column',
              border: '1px solid #f0f0f0',
              borderRadius: 4,
              background: '#fafafa',
              overflow: 'hidden',
            }}
          >
            <div
              ref={listRef}
              style={{
                flex: 1,
                overflow: 'auto',
                padding: 16,
                display: 'flex',
                flexDirection: 'column',
                gap: 12,
              }}
            >
              {msgs.length === 0 && (
                <Empty
                  style={{ marginTop: 60 }}
                  description={
                    templateId
                      ? '上传示例图纸开始训练:AI 会按当前模板配置尝试解析,您纠正后保存为样本'
                      : '请先在上方选择要训练的模板'
                  }
                />
              )}
              {msgs.map((m) => (
                <div
                  key={m.id}
                  style={{
                    display: 'flex',
                    justifyContent:
                      m.role === 'user' ? 'flex-end' : 'flex-start',
                  }}
                >
                  <div
                    style={{
                      maxWidth: '75%',
                      padding: '10px 14px',
                      borderRadius: 8,
                      background: m.role === 'user' ? '#1677ff' : '#fff',
                      color: m.role === 'user' ? '#fff' : 'inherit',
                      border: m.role === 'user' ? 'none' : '1px solid #f0f0f0',
                    }}
                  >
                    {m.role === 'system' && (
                      <Alert
                        type="error"
                        showIcon
                        message={m.text}
                        style={{ maxWidth: 480 }}
                      />
                    )}
                    {m.role === 'user' && m.imageUrl && (
                      <img
                        src={m.imageUrl}
                        alt={m.text}
                        style={{
                          maxWidth: 260,
                          maxHeight: 180,
                          borderRadius: 6,
                          display: 'block',
                        }}
                      />
                    )}
                    {m.text && m.role !== 'system' && (
                      <Paragraph style={{ margin: m.imageUrl ? '6px 0 0' : 0, fontSize: 13 }}>
                        {m.text}
                      </Paragraph>
                    )}
                    {m.role === 'assistant' && m.fields && (
                      <div style={{ marginTop: 8 }}>
                        <FieldBubble
                          msg={m}
                          templateId={templateId ?? ''}
                          onEdited={handleEdited}
                          onSaved={handleSaved}
                          saving={savingId === m.id}
                        />
                      </div>
                    )}
                    {m.role === 'assistant' &&
                      m.text === '正在尝试解析这张示例图纸…' && (
                        <Space>
                          <Spin size="small" />
                          <Text style={{ fontSize: 13 }}>{m.text}</Text>
                        </Space>
                      )}
                  </div>
                </div>
              ))}
            </div>
            {/* 输入区 */}
            <div
              style={{
                borderTop: '1px solid #f0f0f0',
                padding: 12,
                background: '#fff',
                display: 'flex',
                gap: 8,
                alignItems: 'center',
              }}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.png,.jpg,.jpeg,.webp,.docx,.xlsx"
                style={{ display: 'none' }}
                onChange={(e) => {
                  const f = e.target.files?.[0]
                  if (f) setFile(f)
                  e.target.value = ''
                }}
              />
              <Button
                icon={<UploadOutlined />}
                onClick={() => fileInputRef.current?.click()}
              >
                {file ? file.name : '上传示例图纸'}
              </Button>
              <Button
                type="primary"
                icon={<SendOutlined />}
                loading={sending}
                onClick={handleSend}
              >
                让 AI 解析
              </Button>
            </div>
          </div>

          {/* 训练样本侧栏 */}
          <div
            style={{
              flex: '0 0 320px',
              border: '1px solid #f0f0f0',
              borderRadius: 4,
              background: '#fff',
              overflow: 'auto',
              padding: 12,
            }}
          >
            <Divider orientation="left" style={{ marginTop: 0 }}>
              训练样本({samples.length})
            </Divider>
            {templateId ? (
              <SamplePanel
                templateId={templateId}
                samples={samples}
                loading={samplesLoading}
                onReload={reloadSamples}
              />
            ) : (
              <Empty
                description="选择模板后显示其训练样本"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            )}
          </div>
        </div>
      </Content>
    </Layout>
  )
}
