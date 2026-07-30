import { useEffect, useState } from 'react'
import {
  Layout,
  Card,
  Form,
  Select,
  Upload,
  Button,
  Input,
  Typography,
  message,
  Space,
  type UploadFile,
} from 'antd'
import { useNavigate } from 'react-router-dom'
import { templateApi } from '@/lib/api/templates'
import { parseJobApi } from '@/lib/api/parseJobs'
import type { TemplateListItem } from '@/types'

const { Header, Content } = Layout
const { Title } = Typography

const ACCEPT = '.pdf,.png,.jpg,.jpeg,.webp,.docx,.xlsx'

export default function NewParseJobPage() {
  const navigate = useNavigate()
  const [templates, setTemplates] = useState<TemplateListItem[]>([])
  const [templateLoading, setTemplateLoading] = useState(false)
  const [selectedTemplate, setSelectedTemplate] = useState<string>()
  const [file, setFile] = useState<File | null>(null)
  const [drawingName, setDrawingName] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    setTemplateLoading(true)
    templateApi
      .list()
      .then(setTemplates)
      .catch((e: unknown) => {
        const msg = e instanceof Error ? e.message : '加载模板失败'
        message.error(msg)
      })
      .finally(() => setTemplateLoading(false))
  }, [])

  const handleBeforeUpload = (f: File) => {
    setFile(f)
    if (!drawingName) setDrawingName(f.name)
    return false // 阻止 antd 自动上传,由「创建并解析」按钮统一提交
  }

  const handleRemove = () => {
    setFile(null)
    setDrawingName('')
  }

  const handleSubmit = async () => {
    if (!selectedTemplate) {
      message.warning('请选择模板')
      return
    }
    if (!file) {
      message.warning('请上传图纸')
      return
    }
    setSubmitting(true)
    try {
      const name = drawingName.trim() || file.name
      const job = await parseJobApi.create(file, selectedTemplate, name)
      message.success('任务已创建,开始解析...')
      try {
        const runJob = await parseJobApi.run(job.id)
        if (runJob.status === 'failed') {
          message.error('解析失败:' + (runJob.result?.error ?? '未知错误'))
          navigate('/parse-jobs')
          return
        }
        message.success('解析完成')
        navigate(`/parse-jobs/${runJob.id}/review`)
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : '解析执行失败'
        message.error(msg)
        navigate('/parse-jobs')
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '创建任务失败'
      message.error(msg)
    } finally {
      setSubmitting(false)
    }
  }

  const fileList: UploadFile[] = file
    ? [
        {
          uid: '-1',
          name: file.name,
          status: 'done',
          size: file.size,
          type: file.type,
        } as UploadFile,
      ]
    : []

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
          新建解析任务
        </Title>
        <Button onClick={() => navigate('/parse-jobs')}>返回列表</Button>
      </Header>
      <Content
        style={{
          padding: 24,
          display: 'flex',
          justifyContent: 'center',
        }}
      >
        <Card style={{ width: 600 }}>
          <Form layout="vertical">
            <Form.Item label="选择模板" required>
              <Select
                placeholder="请选择模板"
                loading={templateLoading}
                value={selectedTemplate}
                onChange={setSelectedTemplate}
                options={templates.map((t) => ({ label: t.name, value: t.id }))}
                notFoundContent={
                  templateLoading ? '加载中...' : '暂无模板,请先在模板设计中创建'
                }
              />
            </Form.Item>
            <Form.Item label="上传图纸" required>
              <Upload.Dragger
                accept={ACCEPT}
                maxCount={1}
                fileList={fileList}
                beforeUpload={handleBeforeUpload}
                onRemove={handleRemove}
              >
                <p style={{ fontSize: 16, margin: '8px 0' }}>
                  点击或拖拽文件到此区域上传
                </p>
                <p style={{ color: '#888', fontSize: 12, marginBottom: 8 }}>
                  支持 PDF / PNG / JPG / WEBP / DOCX / XLSX
                </p>
              </Upload.Dragger>
            </Form.Item>
            <Form.Item label="图纸名称(可选)">
              <Input
                placeholder="默认使用文件名"
                value={drawingName}
                onChange={(e) => setDrawingName(e.target.value)}
              />
            </Form.Item>
            <Form.Item>
              <Space>
                <Button
                  type="primary"
                  loading={submitting}
                  onClick={handleSubmit}
                >
                  创建并解析
                </Button>
                <Button onClick={() => navigate('/parse-jobs')}>取消</Button>
              </Space>
            </Form.Item>
          </Form>
        </Card>
      </Content>
    </Layout>
  )
}
