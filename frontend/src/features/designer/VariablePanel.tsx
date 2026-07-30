import { useState } from 'react'
import {
  List,
  Tag,
  Switch,
  Button,
  Modal,
  Input,
  InputNumber,
  Select,
  Space,
  Typography,
  message,
  Divider,
  Empty,
} from 'antd'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  AimOutlined,
} from '@ant-design/icons'
import type {
  TemplateVariable,
  SourceType,
  DataType,
  Formula,
  VariablePromptUpsert,
  FormulaUpsert,
  PresetRuleOut,
} from '@/types'
import { variableApi, dagApi } from '@/lib/api/templates'
import { extractVarRefs } from '@/lib/formula/engine'
import FormulaEditor from './FormulaEditor'
import type { SelectedCell } from './UniverSheet'

const { Text } = Typography

const SOURCE_COLOR: Record<SourceType, string> = {
  extract: 'blue',
  database: 'purple',
  formula: 'green',
  manual: 'default',
}

const SOURCE_TEXT: Record<SourceType, string> = {
  extract: '抽取',
  database: '数据库',
  formula: '公式',
  manual: '手动',
}

interface VariablePanelProps {
  variables: TemplateVariable[]
  templateId: string | null
  selectedCell: SelectedCell | null
  presetRules: PresetRuleOut[]
  onChanged: () => void
}

interface VarFormState {
  name: string
  placeholder: string
  sheet: string
  cell: string
  source_type: SourceType
  data_type: DataType
  unit: string
  enabled: boolean
  promptText: string
  confidenceThreshold: number
  outputConstraint: string
  formula: Formula
}

const DEFAULT_FORMULA: Formula = {
  kind: 'custom',
  expression: '',
  dependencies: [],
}

function emptyForm(selectedCell: SelectedCell | null): VarFormState {
  return {
    name: '',
    placeholder: '',
    sheet: selectedCell?.sheet ?? 'Sheet1',
    cell: selectedCell?.cell ?? 'A1',
    source_type: 'extract',
    data_type: 'string',
    unit: '',
    enabled: true,
    promptText: '',
    confidenceThreshold: 0.7,
    outputConstraint: '',
    formula: { ...DEFAULT_FORMULA },
  }
}

function formFromVariable(v: TemplateVariable): VarFormState {
  return {
    name: v.name,
    placeholder: v.placeholder,
    sheet: v.sheet,
    cell: v.cell,
    source_type: v.source_type,
    data_type: v.data_type,
    unit: v.unit ?? '',
    enabled: v.enabled,
    promptText: v.prompt?.prompt ?? '',
    confidenceThreshold: v.prompt?.confidence_threshold ?? 0.7,
    outputConstraint:
      (v.prompt?.output_constraints?.pattern as string | undefined) ?? '',
    formula: v.formula
      ? { ...v.formula }
      : { ...DEFAULT_FORMULA },
  }
}

export default function VariablePanel({
  variables,
  templateId,
  selectedCell,
  presetRules,
  onChanged,
}: VariablePanelProps) {
  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [form, setForm] = useState<VarFormState>(() => emptyForm(selectedCell))
  const [saving, setSaving] = useState(false)

  const openCreate = () => {
    setEditingId(null)
    setForm(emptyForm(selectedCell))
    setModalOpen(true)
  }

  const openEdit = (v: TemplateVariable) => {
    setEditingId(v.id)
    setForm(formFromVariable(v))
    setModalOpen(true)
  }

  const update = (patch: Partial<VarFormState>) => {
    setForm((prev) => {
      const next = { ...prev, ...patch }
      // 名称变化时自动生成 placeholder(若 placeholder 为空或为旧 {name})
      if (patch.name !== undefined) {
        const oldPh = prev.placeholder
        if (!oldPh || oldPh === `{${prev.name}}`) {
          next.placeholder = `{${patch.name}}`
        }
      }
      return next
    })
  }

  const handleDelete = async (v: TemplateVariable) => {
    try {
      await variableApi.remove(v.id)
      message.success(`已删除变量「${v.name}」`)
      onChanged()
    } catch (e: unknown) {
      message.error(e instanceof Error ? e.message : '删除失败')
    }
  }

  const validateDag = async () => {
    if (!templateId) return
    try {
      const res = await dagApi.validate(templateId)
      if (res.valid) {
        message.success('DAG 校验通过:依赖关系无环')
      } else {
        const cycles = res.cycles
          .map((c) => c.join(' -> '))
          .join('; ')
        message.warning(
          `DAG 校验失败:${res.errors.join('; ') || '存在环'}${cycles ? ` [${cycles}]` : ''}`
        )
      }
    } catch (e: unknown) {
      message.error(e instanceof Error ? e.message : 'DAG 校验请求失败')
    }
  }

  const handleSave = async () => {
    if (!templateId) {
      message.error('模板尚未保存,无法添加变量')
      return
    }
    if (!form.name.trim()) {
      message.warning('请填写变量名')
      return
    }
    // 名称唯一性校验
    const dup = variables.find(
      (v) => v.name === form.name.trim() && v.id !== editingId
    )
    if (dup) {
      message.warning('变量名在模板内已存在')
      return
    }

    setSaving(true)
    try {
      const base = {
        name: form.name.trim(),
        placeholder: form.placeholder.trim() || `{${form.name.trim()}}`,
        sheet: form.sheet,
        cell: form.cell,
        source_type: form.source_type,
        data_type: form.data_type,
        unit: form.unit.trim() || null,
        enabled: form.enabled,
        depends_on: [] as string[],
      }

      let varId = editingId
      if (editingId) {
        await variableApi.update(editingId, base)
      } else {
        const created = await variableApi.create(templateId, base)
        varId = created.id
      }

      if (!varId) {
        message.error('未获取到变量 ID')
        return
      }

      // prompt(extract)
      if (form.source_type === 'extract') {
        const promptBody: VariablePromptUpsert = {
          prompt: form.promptText.trim(),
          confidence_threshold: form.confidenceThreshold,
        }
        if (form.outputConstraint.trim()) {
          promptBody.output_constraints = { pattern: form.outputConstraint.trim() }
        }
        await variableApi.upsertPrompt(varId, promptBody)
      }

      // formula
      if (form.source_type === 'formula') {
        const formulaBody: FormulaUpsert = {
          kind: form.formula.kind,
          expression: form.formula.expression,
          dependencies: extractVarRefs(form.formula.expression),
        }
        if (form.formula.preset_rule_id) {
          formulaBody.preset_rule_id = form.formula.preset_rule_id
        }
        await variableApi.upsertFormula(varId, formulaBody)
      }

      message.success(editingId ? '变量已更新' : '变量已创建')
      setModalOpen(false)
      onChanged()
      // 保存后校验 DAG
      validateDag()
    } catch (e: unknown) {
      message.error(e instanceof Error ? e.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '8px 12px',
          borderBottom: '1px solid #f0f0f0',
        }}
      >
        <Text strong>变量列表({variables.length})</Text>
        <Space>
          {selectedCell && (
            <Button
              size="small"
              type="dashed"
              icon={<AimOutlined />}
              onClick={openCreate}
              title={`将选中单元格 ${selectedCell.sheet}!${selectedCell.cell} 设为变量`}
            >
              设为变量 {selectedCell.sheet}!{selectedCell.cell}
            </Button>
          )}
          <Button
            size="small"
            type="primary"
            icon={<PlusOutlined />}
            onClick={openCreate}
            disabled={!templateId}
          >
            新增
          </Button>
        </Space>
      </div>

      <div style={{ flex: 1, overflow: 'auto' }}>
        {variables.length === 0 ? (
          <Empty
            style={{ marginTop: 40 }}
            description={templateId ? '暂无变量,点击新增' : '请先保存模板'}
          />
        ) : (
          <List
            dataSource={variables}
            rowKey="id"
            renderItem={(v) => (
              <List.Item
                style={{ padding: '8px 12px' }}
                actions={[
                  <Button
                    key="edit"
                    size="small"
                    type="link"
                    icon={<EditOutlined />}
                    onClick={() => openEdit(v)}
                  />,
                  <Button
                    key="del"
                    size="small"
                    type="link"
                    danger
                    icon={<DeleteOutlined />}
                    onClick={() => handleDelete(v)}
                  />,
                ]}
              >
                <List.Item.Meta
                  title={
                    <Space size={4}>
                      <Text strong>{v.name}</Text>
                      <Tag color={SOURCE_COLOR[v.source_type]}>
                        {SOURCE_TEXT[v.source_type]}
                      </Tag>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {v.sheet}!{v.cell}
                      </Text>
                    </Space>
                  }
                  description={
                    <Space size={12} style={{ fontSize: 12 }}>
                      <span>
                        <Text type="secondary">占位:</Text>
                        {v.placeholder}
                      </span>
                      <span>
                        <Text type="secondary">类型:</Text>
                        {v.data_type}
                        {v.unit ? ` (${v.unit})` : ''}
                      </span>
                      <span>
                        <Text type="secondary">依赖:</Text>
                        {v.depends_on.length > 0
                          ? v.depends_on.join(', ')
                          : '无'}
                      </span>
                      <Switch
                        size="small"
                        checked={v.enabled}
                        onChange={async (checked) => {
                          try {
                            await variableApi.update(v.id, { enabled: checked })
                            onChanged()
                          } catch (e: unknown) {
                            message.error(
                              e instanceof Error ? e.message : '更新失败'
                            )
                          }
                        }}
                      />
                    </Space>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </div>

      <Modal
        title={editingId ? '编辑变量' : '新增变量'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSave}
        okButtonProps={{ loading: saving }}
        width={620}
        destroyOnClose
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <Space>
            <div style={{ flex: 1 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                变量名 *
              </Text>
              <Input
                value={form.name}
                onChange={(e) => update({ name: e.target.value })}
                placeholder="如 总长"
              />
            </div>
            <div style={{ flex: 1 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                占位符
              </Text>
              <Input
                value={form.placeholder}
                onChange={(e) => update({ placeholder: e.target.value })}
                placeholder="{总长}"
              />
            </div>
          </Space>

          <Space>
            <div>
              <Text type="secondary" style={{ fontSize: 12 }}>
                Sheet
              </Text>
              <Input
                value={form.sheet}
                onChange={(e) => update({ sheet: e.target.value })}
                style={{ width: 120 }}
              />
            </div>
            <div>
              <Text type="secondary" style={{ fontSize: 12 }}>
                单元格
              </Text>
              <Input
                value={form.cell}
                onChange={(e) => update({ cell: e.target.value })}
                style={{ width: 120 }}
              />
            </div>
            <div>
              <Text type="secondary" style={{ fontSize: 12 }}>
                单位
              </Text>
              <Input
                value={form.unit}
                onChange={(e) => update({ unit: e.target.value })}
                style={{ width: 100 }}
                placeholder="mm"
              />
            </div>
          </Space>

          <Space>
            <div>
              <Text type="secondary" style={{ fontSize: 12 }}>
                来源类型
              </Text>
              <Select
                value={form.source_type}
                onChange={(v: SourceType) => update({ source_type: v })}
                style={{ width: 140 }}
                options={(Object.keys(SOURCE_TEXT) as SourceType[]).map((k) => ({
                  label: SOURCE_TEXT[k],
                  value: k,
                }))}
              />
            </div>
            <div>
              <Text type="secondary" style={{ fontSize: 12 }}>
                数据类型
              </Text>
              <Select
                value={form.data_type}
                onChange={(v: DataType) => update({ data_type: v })}
                style={{ width: 140 }}
                options={[
                  { label: 'string', value: 'string' },
                  { label: 'number', value: 'number' },
                  { label: 'integer', value: 'integer' },
                  { label: 'enum', value: 'enum' },
                ]}
              />
            </div>
            <div>
              <Text type="secondary" style={{ fontSize: 12 }}>
                启用
              </Text>
              <div>
                <Switch
                  checked={form.enabled}
                  onChange={(checked) => update({ enabled: checked })}
                />
              </div>
            </div>
          </Space>

          {form.source_type === 'extract' && (
            <>
              <Divider style={{ margin: '4px 0' }} />
              <Text strong style={{ fontSize: 13 }}>
                抽取 Prompt 配置
              </Text>
              <div>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  Prompt 文本
                </Text>
                <Input.TextArea
                  value={form.promptText}
                  onChange={(e) => update({ promptText: e.target.value })}
                  rows={2}
                  placeholder="提示模型识别该字段的说明"
                />
              </div>
              <Space>
                <div>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    置信度阈值
                  </Text>
                  <InputNumber
                    value={form.confidenceThreshold}
                    onChange={(v) =>
                      update({
                        confidenceThreshold: typeof v === 'number' ? v : 0.7,
                      })
                    }
                    min={0}
                    max={1}
                    step={0.1}
                    style={{ width: 120 }}
                  />
                </div>
                <div>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    输出约束(枚举/正则,可选)
                  </Text>
                  <Input
                    value={form.outputConstraint}
                    onChange={(e) =>
                      update({ outputConstraint: e.target.value })
                    }
                    style={{ width: 200 }}
                    placeholder="如 ^(是|否)$"
                  />
                </div>
              </Space>
            </>
          )}

          {form.source_type === 'formula' && (
            <>
              <Divider style={{ margin: '4px 0' }} />
              <Text strong style={{ fontSize: 13 }}>
                公式配置
              </Text>
              <FormulaEditor
                value={form.formula}
                onChange={(f) => update({ formula: f })}
                variables={variables}
                presetRules={presetRules}
              />
            </>
          )}
        </div>
      </Modal>
    </div>
  )
}
