import client from './client'
import type {
  TemplateOut,
  TemplateListItem,
  TemplateVariable,
  VariableCreate,
  VariableUpdate,
  VariablePrompt,
  VariablePromptUpsert,
  Formula,
  FormulaUpsert,
  MappingOut,
  MappingCreate,
  MappingUpdate,
  DagValidateResult,
  FormulaEvaluateRequest,
  FormulaEvaluateResponse,
  PresetRuleOut,
  PresetRuleCreate,
} from '@/types'

/** 模板 API */
export const templateApi = {
  /** 模板列表 */
  list(): Promise<TemplateListItem[]> {
    return client
      .get<TemplateListItem[]>('/templates')
      .then((res) => res.data)
  },

  /** 模板详情(含 variables) */
  get(id: string): Promise<TemplateOut> {
    return client.get<TemplateOut>(`/templates/${id}`).then((res) => res.data)
  },

  /** 创建模板 */
  create(body: {
    name: string
    univer_snapshot?: Record<string, unknown>
  }): Promise<TemplateOut> {
    return client.post<TemplateOut>('/templates', body).then((res) => res.data)
  },

  /** 更新模板 */
  update(
    id: string,
    body: { name?: string; univer_snapshot?: Record<string, unknown> }
  ): Promise<TemplateOut> {
    return client.put<TemplateOut>(`/templates/${id}`, body).then((res) => res.data)
  },

  /** 删除模板 */
  remove(id: string): Promise<void> {
    return client.delete(`/templates/${id}`).then(() => undefined)
  },
}

/** 变量 API */
export const variableApi = {
  /** 列出模板下所有变量 */
  listByTemplate(templateId: string): Promise<TemplateVariable[]> {
    return client
      .get<TemplateVariable[]>(`/templates/${templateId}/variables`)
      .then((res) => res.data)
  },

  /** 创建变量 */
  create(
    templateId: string,
    body: VariableCreate
  ): Promise<TemplateVariable> {
    return client
      .post<TemplateVariable>(`/templates/${templateId}/variables`, body)
      .then((res) => res.data)
  },

  /** 更新变量 */
  update(id: string, patch: VariableUpdate): Promise<TemplateVariable> {
    return client
      .put<TemplateVariable>(`/variables/${id}`, patch)
      .then((res) => res.data)
  },

  /** 删除变量 */
  remove(id: string): Promise<void> {
    return client.delete(`/variables/${id}`).then(() => undefined)
  },

  /** upsert 变量的 prompt 配置 */
  upsertPrompt(id: string, body: VariablePromptUpsert): Promise<VariablePrompt> {
    return client
      .put<VariablePrompt>(`/variables/${id}/prompt`, body)
      .then((res) => res.data)
  },

  /** upsert 变量的公式配置 */
  upsertFormula(id: string, body: FormulaUpsert): Promise<Formula> {
    return client
      .put<Formula>(`/variables/${id}/formula`, body)
      .then((res) => res.data)
  },
}

/** 字段映射 API */
export const mappingApi = {
  /** 列出模板下所有映射 */
  listByTemplate(templateId: string): Promise<MappingOut[]> {
    return client
      .get<MappingOut[]>(`/templates/${templateId}/mappings`)
      .then((res) => res.data)
  },

  /** 创建映射 */
  create(templateId: string, body: MappingCreate): Promise<MappingOut> {
    return client
      .post<MappingOut>(`/templates/${templateId}/mappings`, body)
      .then((res) => res.data)
  },

  /** 更新映射 */
  update(id: string, patch: MappingUpdate): Promise<MappingOut> {
    return client
      .put<MappingOut>(`/mappings/${id}`, patch)
      .then((res) => res.data)
  },

  /** 删除映射 */
  remove(id: string): Promise<void> {
    return client.delete(`/mappings/${id}`).then(() => undefined)
  },
}

/** DAG 校验 API */
export const dagApi = {
  /** 校验模板变量依赖图是否无环 */
  validate(templateId: string): Promise<DagValidateResult> {
    return client
      .post<DagValidateResult>(`/templates/${templateId}/validate-dag`)
      .then((res) => res.data)
  },
}

/** 公式求值 API */
export const formulaApi = {
  /** 调用后端求值公式 */
  evaluate(req: FormulaEvaluateRequest): Promise<FormulaEvaluateResponse> {
    return client
      .post<FormulaEvaluateResponse>('/formula/evaluate', req)
      .then((res) => res.data)
  },
}

/** 预设规则 API */
export const presetRuleApi = {
  /** 列出所有预设规则 */
  list(): Promise<PresetRuleOut[]> {
    return client.get<PresetRuleOut[]>('/preset-rules').then((res) => res.data)
  },

  /** 创建预设规则 */
  create(body: PresetRuleCreate): Promise<PresetRuleOut> {
    return client
      .post<PresetRuleOut>('/preset-rules', body)
      .then((res) => res.data)
  },
}

export default templateApi
