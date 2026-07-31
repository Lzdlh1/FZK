import client from './client'
import type { RuleCreate, RuleOut, RuleUpdate } from '@/types'

export const ruleApi = {
  list(params?: { category?: string; enabled?: boolean }): Promise<RuleOut[]> {
    return client.get<RuleOut[]>('/rules', { params }).then((res) => res.data)
  },

  create(data: RuleCreate): Promise<RuleOut> {
    return client.post<RuleOut>('/rules', data).then((res) => res.data)
  },

  update(id: string, data: RuleUpdate): Promise<RuleOut> {
    return client.put<RuleOut>(`/rules/${id}`, data).then((res) => res.data)
  },

  delete(id: string): Promise<void> {
    return client.delete(`/rules/${id}`).then(() => undefined)
  },
}
