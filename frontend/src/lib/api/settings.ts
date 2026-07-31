import client from './client'
import type {
  AIProviderCreate,
  AIProviderHealthResult,
  AIProviderOut,
  AIProviderUpdate,
  DatabaseParamCreate,
  DatabaseParamOut,
  DatabaseParamUpdate,
} from '@/types'

/* ---- AI 供应商 ---- */

export const aiProviderApi = {
  list(): Promise<AIProviderOut[]> {
    return client.get<AIProviderOut[]>('/settings/ai-providers').then((res) => res.data)
  },

  create(data: AIProviderCreate): Promise<AIProviderOut> {
    return client.post<AIProviderOut>('/settings/ai-providers', data).then((res) => res.data)
  },

  update(id: string, data: AIProviderUpdate): Promise<AIProviderOut> {
    return client.put<AIProviderOut>(`/settings/ai-providers/${id}`, data).then((res) => res.data)
  },

  delete(id: string): Promise<void> {
    return client.delete(`/settings/ai-providers/${id}`).then(() => undefined)
  },

  checkHealth(id: string): Promise<AIProviderHealthResult> {
    return client
      .post<AIProviderHealthResult>(`/settings/ai-providers/${id}/health`)
      .then((res) => res.data)
  },
}

/* ---- 数据库参数 ---- */

export const databaseParamApi = {
  list(category?: string): Promise<DatabaseParamOut[]> {
    const params = category ? { category } : {}
    return client
      .get<DatabaseParamOut[]>('/settings/database-params', { params })
      .then((res) => res.data)
  },

  create(data: DatabaseParamCreate): Promise<DatabaseParamOut> {
    return client.post<DatabaseParamOut>('/settings/database-params', data).then((res) => res.data)
  },

  update(id: string, data: DatabaseParamUpdate): Promise<DatabaseParamOut> {
    return client.put<DatabaseParamOut>(`/settings/database-params/${id}`, data).then((res) => res.data)
  },

  delete(id: string): Promise<void> {
    return client.delete(`/settings/database-params/${id}`).then(() => undefined)
  },

  /** 导出为 Excel 文件 */
  async exportExcel(): Promise<void> {
    const res = await client.get('/settings/database-params/export', { responseType: 'blob' })
    const url = window.URL.createObjectURL(res.data)
    const a = document.createElement('a')
    a.href = url
    a.download = 'database_params.xlsx'
    a.click()
    window.URL.revokeObjectURL(url)
  },

  /** 从 Excel 文件导入 */
  async importExcel(file: File): Promise<{ imported: number; skipped: number }> {
    const formData = new FormData()
    formData.append('file', file)
    // 不要手动设 Content-Type:axios 会自动生成带 boundary 的
    // multipart/form-data;手动设反而会丢 boundary 导致 422
    const res = await client.post<{ imported: number; skipped: number }>(
      '/settings/database-params/import',
      formData
    )
    return res.data
  },
}
