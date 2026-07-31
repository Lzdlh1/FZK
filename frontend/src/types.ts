/** 用户信息 */
export interface User {
  id: string | number
  name: string
  role: string
}

/** 登录接口返回 */
export interface LoginResponse {
  access_token: string
  token_type: string
  user: User
}

/** 登录请求体 */
export interface LoginRequest {
  name: string
  password: string
}

/* ===================== 模板相关(与后端 schemas/template.py 对齐) ===================== */

/** 变量来源类型 */
export type SourceType = 'extract' | 'database' | 'formula' | 'manual'

/** 变量数据类型 */
export type DataType = 'string' | 'number' | 'integer' | 'enum'

/** 抽取型变量的 prompt 配置 */
export interface VariablePrompt {
  /** 提示文本 */
  prompt: string
  /** 输出约束(枚举/正则等) */
  output_constraints?: Record<string, unknown>
  /** 置信度阈值,低于该值标记为低置信;默认 0.7 */
  confidence_threshold: number
  /** 后处理配置 */
  post_process?: Record<string, unknown>
}

/** 公式定义 */
export interface Formula {
  kind: 'preset' | 'custom'
  expression: string
  preset_rule_id?: string
  dependencies: string[]
}

/** 模板变量定义 */
export interface TemplateVariable {
  id: string
  name: string
  placeholder: string
  sheet: string
  cell: string
  source_type: SourceType
  data_type: DataType
  unit?: string | null
  enabled: boolean
  depends_on: string[]
  prompt?: VariablePrompt | null
  formula?: Formula | null
}

/** 模板输出(完整版) */
export interface TemplateOut {
  id: string
  name: string
  version: number
  updated_at?: string
  owner_id?: string
  /** Univer IUniverSnapshot 序列化 JSON */
  univer_snapshot?: Record<string, unknown>
  variables: TemplateVariable[]
}

/** 模板列表项 */
export interface TemplateListItem {
  id: string
  name: string
  version: number
  updated_at?: string
}

/** 变量创建请求体 */
export interface VariableCreate {
  name: string
  placeholder?: string
  sheet: string
  cell: string
  source_type: SourceType
  data_type: DataType
  unit?: string | null
  enabled?: boolean
  depends_on?: string[]
}

/** 变量更新请求体 */
export interface VariableUpdate {
  name?: string
  placeholder?: string
  sheet?: string
  cell?: string
  source_type?: SourceType
  data_type?: DataType
  unit?: string | null
  enabled?: boolean
  depends_on?: string[]
}

/** 变量 prompt upsert 请求体 */
export interface VariablePromptUpsert {
  prompt: string
  output_constraints?: Record<string, unknown>
  confidence_threshold?: number
  post_process?: Record<string, unknown>
}

/** 公式 upsert 请求体 */
export interface FormulaUpsert {
  kind: 'preset' | 'custom'
  expression: string
  preset_rule_id?: string
  dependencies: string[]
}

/** 字段映射创建请求体 */
export interface MappingCreate {
  /** 变量 placeholder -> 来源键名,或具体映射字段 */
  variable_id?: string
  source_key: string
  target_field: string
  config?: Record<string, unknown>
}

/** 字段映射更新请求体 */
export interface MappingUpdate {
  variable_id?: string
  source_key?: string
  target_field?: string
  config?: Record<string, unknown>
}

/** 字段映射输出 */
export interface MappingOut {
  id: string
  template_id: string
  variable_id?: string
  source_key: string
  target_field: string
  config?: Record<string, unknown>
}

/** 预设规则创建请求体 */
export interface PresetRuleCreate {
  name: string
  /** 表达式模板,如 "{总长} - {吃线} * {端子数}" */
  expression_template: string
  /** 参数名列表 */
  params?: string[]
  description?: string
}

/** 预设规则输出 */
export interface PresetRuleOut {
  id: string
  name: string
  expression_template: string
  params: string[]
  description?: string
}

/** DAG 校验结果 */
export interface DagValidateResult {
  valid: boolean
  cycles: string[][]
  errors: string[]
}

/** 公式求值请求体 */
export interface FormulaEvaluateRequest {
  expression: string
  values: Record<string, number>
}

/** 公式求值响应 */
export interface FormulaEvaluateResponse {
  value: number
  substituted_expression: string
  db_refs: unknown[]
}

/* ===================== 解析任务相关 ===================== */

/** 字段来源区域(bbox 归一化到 [0,1]) */
export interface SourceRegion {
  page: number
  bbox: [number, number, number, number] // [x, y, w, h]
}

/** 候选值 */
export interface FieldAlternative {
  value: unknown
  confidence: number
}

/** DB 引用项 */
export interface DbRef {
  var: string
  value: unknown
  version: string
}

/** 字段状态 */
export type FieldStatus =
  | 'extracted'
  | 'low_confidence'
  | 'not_found'
  | 'error'
  | 'manual'
  | 'formula'
  | string

/** 单个字段解析结果 */
export interface FieldResult {
  value: unknown
  confidence: number | null
  source_region: SourceRegion | null
  raw_text: string | null
  unit: string | null
  alternatives: FieldAlternative[]
  status: FieldStatus
  /** formula 型字段:替换后的可读表达式,如 "开线长度 = 1000 - 12×2 = 976" */
  substituted_expression: string | null
  /** formula 型字段:依赖的 DB 参数引用 */
  db_refs: DbRef[] | null
  error: string | null
}

/** 解析任务结果 */
export interface ParseJobResult {
  fields: Record<string, FieldResult>
  meta: Record<string, unknown>
  error: string | null
}

/** 解析任务状态 */
export type ParseJobStatus = 'pending' | 'parsing' | 'review' | 'done' | 'failed'

/** 解析任务输出(详情) */
export interface ParseJobOut {
  id: string
  template_id: string
  drawing_name: string
  status: ParseJobStatus
  result: ParseJobResult | null
  created_at: string
  template: TemplateOut | null
}

/** 解析任务列表项 */
export interface ParseJobListItem {
  id: string
  template_id: string
  drawing_name: string
  status: ParseJobStatus
  created_at: string
  template?: TemplateOut | null
}

/** 审核请求体 */
export interface ReviewRequest {
  edits: Record<string, unknown>
  manual_overrides: string[]
}

/** 单字段重跑返回 */
export interface RerunFieldResponse {
  field: FieldResult
}

/** 输出请求体 */
export interface OutputRequest {
  filename?: string
}

/** 输出响应 */
export interface OutputResponse {
  output_url: string
  snapshot_id: string
  filename: string
}

/** 历史快照输出 */
export interface HistorySnapshotOut {
  id: string
  parse_job_id: string
  drawing_oid: string
  template_snapshot: Record<string, unknown>
  db_version: Record<string, unknown>
  rule_version: Record<string, unknown>
  ai_raw_result: Record<string, unknown>
  manual_edits: Record<string, unknown>
  output_oid: string | null
  created_at: string
}

/* ===================== 设置相关 ===================== */

/** AI 供应商输出 */
export interface AIProviderOut {
  id: string
  name: string
  endpoint: string
  model: string
  weight: number
  healthy: boolean
  last_check_at: string | null
}

/** AI 供应商创建请求 */
export interface AIProviderCreate {
  name: string
  endpoint: string
  api_key: string
  model: string
  weight?: number
  healthy?: boolean
}

/** AI 供应商更新请求 */
export interface AIProviderUpdate {
  name?: string
  endpoint?: string
  api_key?: string
  model?: string
  weight?: number
  healthy?: boolean
}

/** AI 供应商健康检查结果 */
export interface AIProviderHealthResult {
  id: string
  name: string
  healthy: boolean
  error: string | null
}

/** 数据库参数输出 */
export interface DatabaseParamOut {
  id: string
  category: string
  model: string
  field: string
  value: string
  unit: string | null
  enabled: boolean
  version: number
}

/** 数据库参数创建请求 */
export interface DatabaseParamCreate {
  category: string
  model: string
  field: string
  value: string
  unit?: string | null
  enabled?: boolean
}

/** 数据库参数更新请求 */
export interface DatabaseParamUpdate {
  category?: string
  model?: string
  field?: string
  value?: string
  unit?: string | null
  enabled?: boolean
}
