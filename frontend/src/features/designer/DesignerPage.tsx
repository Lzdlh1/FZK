import { useEffect, useRef, useState } from 'react'
import {
  Layout,
  Input,
  Button,
  Space,
  Typography,
  Spin,
  Tag,
  message,
  Modal,
  Result,
  Alert,
} from 'antd'
import {
  ArrowLeftOutlined,
  FileAddOutlined,
  ImportOutlined,
  SaveOutlined,
  ExportOutlined,
  ApartmentOutlined,
} from '@ant-design/icons'
import { useNavigate, useParams, useLocation } from 'react-router-dom'
import { templateApi, variableApi, dagApi, presetRuleApi } from '@/lib/api/templates'
import {
  createEmptySnapshot,
  importXlsx,
  exportXlsx,
  type IUniverSnapshot,
} from '@/lib/univer/snapshot'
import type {
  TemplateVariable,
  PresetRuleOut,
  DagValidateResult,
} from '@/types'
import UniverSheet, { type UniverSheetHandle, type SelectedCell } from './UniverSheet'
import VariablePanel from './VariablePanel'

const { Header, Content } = Layout
const { Title, Text } = Typography

export default function DesignerPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { templateId } = useParams<{ templateId?: string }>()
  const tid = templateId ?? null

  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [templateName, setTemplateName] = useState('')
  const [version, setVersion] = useState<number | null>(null)
  const [initialSnapshot, setInitialSnapshot] = useState<IUniverSnapshot | null>(
    null
  )
  const [sheetKey, setSheetKey] = useState(0)
  const [variables, setVariables] = useState<TemplateVariable[]>([])
  const [presetRules, setPresetRules] = useState<PresetRuleOut[]>([])
  const [selectedCell, setSelectedCell] = useState<SelectedCell | null>(null)
  const [dagOpen, setDagOpen] = useState(false)
  const [dagResult, setDagResult] = useState<DagValidateResult | null>(null)

  const sheetRef = useRef<UniverSheetHandle>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // 预设规则只加载一次
  useEffect(() => {
    presetRuleApi
      .list()
      .then(setPresetRules)
      .catch(() => {
        // 预设规则加载失败不阻塞设计器
      })
  }, [])

  // 加载模板
  useEffect(() => {
    if (tid) {
      setLoading(true)
      templateApi
        .get(tid)
        .then((t) => {
          setTemplateName(t.name)
          setVersion(t.version)
          setVariables(t.variables ?? [])
          setInitialSnapshot(
            (t.univer_snapshot as IUniverSnapshot | undefined) ??
              createEmptySnapshot()
          )
          setSheetKey((k) => k + 1)
        })
        .catch((e: unknown) => {
          message.error(e instanceof Error ? e.message : '加载模板失败')
          setInitialSnapshot(createEmptySnapshot())
          setSheetKey((k) => k + 1)
        })
        .finally(() => setLoading(false))
    } else {
      // 新建模式:若来自"复制"则携带 snapshot 与 name
      const state = location.state as
        | { snapshot?: IUniverSnapshot; name?: string }
        | null
      setTemplateName(state?.name ?? '')
      setVersion(null)
      setVariables([])
      setInitialSnapshot(state?.snapshot ?? createEmptySnapshot())
      setSheetKey((k) => k + 1)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tid])

  const reloadVariables = () => {
    if (!tid) {
      setVariables([])
      return
    }
    variableApi
      .listByTemplate(tid)
      .then(setVariables)
      .catch((e: unknown) => {
        message.error(e instanceof Error ? e.message : '加载变量失败')
      })
  }

  const handleSave = async () => {
    if (!templateName.trim()) {
      message.warning('请填写模板名')
      return
    }
    const snap = sheetRef.current?.getSnapshot()
    if (!snap) {
      message.warning('表格未就绪')
      return
    }
    setSaving(true)
    try {
      if (tid) {
        await templateApi.update(tid, {
          name: templateName.trim(),
          univer_snapshot: snap,
        })
        message.success('已保存')
        templateApi
          .get(tid)
          .then((t) => setVersion(t.version))
          .catch(() => undefined)
      } else {
        const created = await templateApi.create({
          name: templateName.trim(),
          univer_snapshot: snap,
        })
        message.success('模板已创建')
        navigate(`/designer/${created.id}`)
      }
    } catch (e: unknown) {
      message.error(e instanceof Error ? e.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

  const handleNewBlank = () => {
    setInitialSnapshot(createEmptySnapshot())
    setSheetKey((k) => k + 1)
    message.info('已重置为空白表格')
  }

  const handleImportClick = () => {
    fileInputRef.current?.click()
  }

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    try {
      const snap = await importXlsx(file)
      setInitialSnapshot(snap)
      setSheetKey((k) => k + 1)
      message.success(`已导入 ${file.name}`)
    } catch (err: unknown) {
      message.error(err instanceof Error ? err.message : '导入 xlsx 失败')
    }
  }

  const handleSaveAs = async () => {
    const snap = sheetRef.current?.getSnapshot()
    if (!snap) return
    const name = `${templateName.trim() || '模板'} 副本`
    try {
      const created = await templateApi.create({
        name,
        univer_snapshot: snap,
      })
      message.success('已另存为新模板')
      navigate(`/designer/${created.id}`)
    } catch (e: unknown) {
      message.error(e instanceof Error ? e.message : '另存失败')
    }
  }

  const handleExport = () => {
    const snap = sheetRef.current?.getSnapshot()
    if (!snap) return
    exportXlsx(snap, templateName.trim() || '模板')
  }

  const handleValidateDag = async () => {
    if (!tid) {
      message.warning('请先保存模板后再校验 DAG')
      return
    }
    try {
      const res = await dagApi.validate(tid)
      setDagResult(res)
      setDagOpen(true)
    } catch (e: unknown) {
      message.error(e instanceof Error ? e.message : 'DAG 校验请求失败')
    }
  }

  if (loading) {
    return (
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100vh',
        }}
      >
        <Spin size="large" />
      </div>
    )
  }

  return (
    <Layout style={{ height: '100vh' }}>
      <Header
        style={{
          background: '#fff',
          padding: '0 12px',
          borderBottom: '1px solid #f0f0f0',
          height: 'auto',
          lineHeight: 'normal',
          display: 'flex',
          flexDirection: 'column',
          gap: 6,
          flex: '0 0 auto',
        }}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <Space>
            <Button
              icon={<ArrowLeftOutlined />}
              onClick={() => navigate('/templates')}
            >
              返回
            </Button>
            <Title level={5} style={{ margin: 0 }}>
              {tid ? '编辑模板' : '新建模板'}
            </Title>
            {version != null && <Tag color="blue">v{version}</Tag>}
          </Space>
          <Space>
            <Input
              value={templateName}
              onChange={(e) => setTemplateName(e.target.value)}
              placeholder="模板名称"
              style={{ width: 220 }}
            />
            <Button
              type="primary"
              icon={<SaveOutlined />}
              loading={saving}
              onClick={handleSave}
            >
              保存
            </Button>
          </Space>
        </div>
        <Space size={6} wrap>
          <Button size="small" icon={<FileAddOutlined />} onClick={handleNewBlank}>
            新建空白
          </Button>
          <Button
            size="small"
            icon={<ImportOutlined />}
            onClick={handleImportClick}
          >
            导入 xlsx
          </Button>
          <Button size="small" icon={<SaveOutlined />} onClick={handleSaveAs}>
            另存为
          </Button>
          <Button size="small" icon={<ExportOutlined />} onClick={handleExport}>
            导出 xlsx
          </Button>
          <Button
            size="small"
            icon={<ApartmentOutlined />}
            onClick={handleValidateDag}
            disabled={!tid}
          >
            校验 DAG
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".xlsx"
            style={{ display: 'none' }}
            onChange={handleFileChange}
          />
        </Space>
      </Header>
      <Content style={{ padding: 8, overflow: 'hidden' }}>
        <div style={{ display: 'flex', gap: 8, height: '100%' }}>
          <div
            style={{
              flex: '1 1 60%',
              minWidth: 0,
              border: '1px solid #f0f0f0',
              borderRadius: 4,
              overflow: 'hidden',
              background: '#fff',
            }}
          >
            {initialSnapshot && (
              <UniverSheet
                key={sheetKey}
                ref={sheetRef}
                initialSnapshot={initialSnapshot}
                onSelectionChange={setSelectedCell}
              />
            )}
          </div>
          <div
            style={{
              flex: '1 1 40%',
              minWidth: 320,
              maxWidth: 480,
              border: '1px solid #f0f0f0',
              borderRadius: 4,
              overflow: 'hidden',
              background: '#fff',
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            <VariablePanel
              variables={variables}
              templateId={tid}
              selectedCell={selectedCell}
              presetRules={presetRules}
              onChanged={reloadVariables}
            />
          </div>
        </div>
      </Content>

      <Modal
        title="DAG 校验结果"
        open={dagOpen}
        onCancel={() => setDagOpen(false)}
        footer={[
          <Button key="ok" type="primary" onClick={() => setDagOpen(false)}>
            确定
          </Button>,
        ]}
      >
        {dagResult ? (
          dagResult.valid ? (
            <Result status="success" title="依赖关系无环" />
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <Alert type="error" showIcon message="检测到依赖环或错误" />
              {dagResult.errors.length > 0 && (
                <div>
                  <Text strong>错误:</Text>
                  <ul style={{ margin: '4px 0', paddingLeft: 20 }}>
                    {dagResult.errors.map((err, i) => (
                      <li key={i}>{err}</li>
                    ))}
                  </ul>
                </div>
              )}
              {dagResult.cycles.length > 0 && (
                <div>
                  <Text strong>环:</Text>
                  <ul style={{ margin: '4px 0', paddingLeft: 20 }}>
                    {dagResult.cycles.map((c, i) => (
                      <li key={i}>{c.join(' -> ')}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )
        ) : (
          <Text>无结果</Text>
        )}
      </Modal>
    </Layout>
  )
}
