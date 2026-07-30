import { useEffect, useMemo, useState } from 'react'
import { Radio, Select, Input, Typography, Alert, Space, Tag, Empty } from 'antd'
import type { Formula, TemplateVariable, PresetRuleOut } from '@/types'
import { evaluate, extractVarRefs } from '@/lib/formula/engine'

const { Text, Paragraph } = Typography
const { TextArea } = Input

interface FormulaEditorProps {
  value: Formula
  onChange: (f: Formula) => void
  variables: TemplateVariable[]
  presetRules: PresetRuleOut[]
}

function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

/** 根据模式与绑定构建最终表达式 */
function buildExpression(
  kind: 'preset' | 'custom',
  rawExpr: string,
  rule: PresetRuleOut | undefined,
  bindings: Record<string, string>
): string {
  if (kind === 'custom') return rawExpr
  if (!rule) return rawExpr
  let expr = rule.expression_template
  for (const p of rule.params) {
    const varName = bindings[p]
    const replacement = varName ? `{${varName}}` : `{${p}}`
    expr = expr.replace(new RegExp(`\\{${escapeRegExp(p)}\\}`, 'g'), replacement)
  }
  return expr
}

export default function FormulaEditor({
  value,
  onChange,
  variables,
  presetRules,
}: FormulaEditorProps) {
  const [kind, setKind] = useState<'preset' | 'custom'>(value.kind)
  const [expression, setExpression] = useState<string>(value.expression)
  const [presetRuleId, setPresetRuleId] = useState<string | undefined>(
    value.preset_rule_id
  )
  const [paramBindings, setParamBindings] = useState<Record<string, string>>({})

  // 恢复 preset 模式下的参数绑定(启发式:按出现顺序映射)
  useEffect(() => {
    if (value.kind === 'preset' && value.preset_rule_id) {
      const rule = presetRules.find((r) => r.id === value.preset_rule_id)
      if (rule && rule.params.length > 0) {
        const varsInExpr = extractVarRefs(value.expression)
        const bindings: Record<string, string> = {}
        rule.params.forEach((p, i) => {
          if (varsInExpr[i]) bindings[p] = varsInExpr[i]
        })
        setParamBindings(bindings)
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value])

  const selectedRule = useMemo(
    () => presetRules.find((r) => r.id === presetRuleId),
    [presetRules, presetRuleId]
  )

  const currentExpression = useMemo(
    () => buildExpression(kind, expression, selectedRule, paramBindings),
    [kind, expression, selectedRule, paramBindings]
  )

  const preview = useMemo(() => {
    const refs = extractVarRefs(currentExpression)
    const testValues: Record<string, number> = {}
    for (const r of refs) testValues[r] = 1
    try {
      const res = evaluate(currentExpression, testValues)
      return { value: res.value, sub: res.substitutedExpression, refs, error: null as string | null }
    } catch (e) {
      return {
        value: null as number | null,
        sub: null as string | null,
        refs,
        error: e instanceof Error ? e.message : '表达式无效',
      }
    }
  }, [currentExpression])

  const emit = (next: {
    kind: 'preset' | 'custom'
    expr: string
    ruleId?: string
  }) => {
    onChange({
      kind: next.kind,
      expression: next.expr,
      preset_rule_id: next.kind === 'preset' ? next.ruleId : undefined,
      dependencies: extractVarRefs(next.expr),
    })
  }

  const handleKindChange = (k: 'preset' | 'custom') => {
    setKind(k)
    const rule = presetRules.find((r) => r.id === presetRuleId)
    const expr = buildExpression(k, expression, rule, paramBindings)
    emit({ kind: k, expr, ruleId: presetRuleId })
  }

  const handleExpressionChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const v = e.target.value
    setExpression(v)
    emit({ kind, expr: v, ruleId: presetRuleId })
  }

  const handleRuleChange = (ruleId: string) => {
    setPresetRuleId(ruleId)
    const rule = presetRules.find((r) => r.id === ruleId)
    const expr = buildExpression(kind, expression, rule, paramBindings)
    emit({ kind, expr, ruleId })
  }

  const handleBindingChange = (param: string, varName: string) => {
    const nextBindings = { ...paramBindings, [param]: varName }
    setParamBindings(nextBindings)
    const rule = presetRules.find((r) => r.id === presetRuleId)
    const expr = buildExpression(kind, expression, rule, nextBindings)
    emit({ kind, expr, ruleId: presetRuleId })
  }

  const varOptions = variables.map((v) => ({
    label: `${v.name} (${v.placeholder})`,
    value: v.name,
  }))

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <Radio.Group
        value={kind}
        onChange={(e) => handleKindChange(e.target.value)}
        optionType="button"
        buttonStyle="solid"
        size="small"
      >
        <Radio.Button value="preset">预设规则</Radio.Button>
        <Radio.Button value="custom">自定义</Radio.Button>
      </Radio.Group>

      {kind === 'preset' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <Select
            placeholder="选择预设规则"
            value={presetRuleId}
            onChange={handleRuleChange}
            options={presetRules.map((r) => ({
              label: r.name,
              value: r.id,
            }))}
            size="small"
            notFoundContent={
              presetRules.length === 0 ? '暂无预设规则' : undefined
            }
          />
          {selectedRule ? (
            selectedRule.params.length === 0 ? (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description="该规则无参数"
              />
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {selectedRule.params.map((p) => (
                  <Space key={p} align="center">
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      参数 {p}:
                    </Text>
                    <Select
                      size="small"
                      style={{ minWidth: 160 }}
                      placeholder="绑定变量"
                      value={paramBindings[p]}
                      onChange={(v) => handleBindingChange(p, v)}
                      options={varOptions}
                      allowClear
                    />
                  </Space>
                ))}
              </div>
            )
          ) : (
            !presetRuleId && (
              <Text type="secondary" style={{ fontSize: 12 }}>
                请选择预设规则
              </Text>
            )
          )}
          {selectedRule && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              模板:{selectedRule.expression_template}
            </Text>
          )}
        </div>
      )}

      {kind === 'custom' && (
        <TextArea
          value={expression}
          onChange={handleExpressionChange}
          rows={3}
          placeholder="如 {总长} - {吃线} * {端子数}"
          size="small"
        />
      )}

      {/* 实时预览 */}
      <div
        style={{
          background: '#fafafa',
          border: '1px solid #f0f0f0',
          borderRadius: 4,
          padding: 8,
        }}
      >
        <Text type="secondary" style={{ fontSize: 12 }}>
          当前表达式
        </Text>
        <Paragraph style={{ margin: '4px 0', fontFamily: 'monospace' }}>
          {currentExpression || '(空)'}
        </Paragraph>
        {preview.error ? (
          <Alert
            type="error"
            showIcon
            message={preview.error}
            style={{ marginTop: 4 }}
          />
        ) : (
          <Space direction="vertical" size={2} style={{ width: '100%' }}>
            <Text style={{ fontSize: 12 }}>
              预览值:<Text strong>{preview.value}</Text>
            </Text>
            <Text type="secondary" style={{ fontSize: 12 }}>
              替换后:{preview.sub}
            </Text>
            <div>
              <Text type="secondary" style={{ fontSize: 12 }}>
                依赖变量:
              </Text>{' '}
              {preview.refs.length === 0 ? (
                <Text type="secondary" style={{ fontSize: 12 }}>
                  无
                </Text>
              ) : (
                preview.refs.map((r) => (
                  <Tag key={r} style={{ marginBottom: 2 }}>
                    {r}
                  </Tag>
                ))
              )}
            </div>
          </Space>
        )}
      </div>
    </div>
  )
}
