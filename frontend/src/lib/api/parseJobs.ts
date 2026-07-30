import client from './client'
import type {
  ParseJobOut,
  ParseJobListItem,
  ReviewRequest,
  RerunFieldResponse,
} from '@/types'

export const parseJobApi = {
  /** 创建解析任务(multipart 上传) */
  create(
    file: File,
    templateId: string,
    drawingName?: string
  ): Promise<ParseJobOut> {
    const form = new FormData()
    form.append('file', file)
    form.append('template_id', templateId)
    if (drawingName) form.append('drawing_name', drawingName)
    return client
      .post<ParseJobOut>('/parse-jobs', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      .then((res) => res.data)
  },

  /** 任务列表 */
  list(): Promise<ParseJobListItem[]> {
    return client.get<ParseJobListItem[]>('/parse-jobs').then((res) => res.data)
  },

  /** 任务详情(含 result.fields + template.variables) */
  get(id: string): Promise<ParseJobOut> {
    return client.get<ParseJobOut>(`/parse-jobs/${id}`).then((res) => res.data)
  },

  /** 同步执行解析 */
  run(id: string): Promise<ParseJobOut> {
    return client
      .post<ParseJobOut>(`/parse-jobs/${id}/run`)
      .then((res) => res.data)
  },

  /** 单字段重新识别(整图重跑) */
  rerunField(id: string, variableId: string): Promise<RerunFieldResponse> {
    return client
      .post<RerunFieldResponse>(`/parse-jobs/${id}/rerun-field`, {
        variable_id: variableId,
      })
      .then((res) => res.data)
  },

  /** 保存审核 */
  review(
    id: string,
    edits: Record<string, unknown>,
    manualOverrides: string[]
  ): Promise<ParseJobOut> {
    const body: ReviewRequest = {
      edits,
      manual_overrides: manualOverrides,
    }
    return client
      .put<ParseJobOut>(`/parse-jobs/${id}/review`, body)
      .then((res) => res.data)
  },
}

/**
 * 拉取图纸二进制并创建 ObjectURL。
 * 该接口需鉴权,通过 axios 带 Authorization 头,以 blob 形式接收后转 ObjectURL。
 * 调用方负责在不再使用时 URL.revokeObjectURL(url)。
 */
export async function getDrawingObjectUrl(
  id: string
): Promise<{ url: string; contentType: string }> {
  const resp = await client.get(`/parse-jobs/${id}/drawing`, {
    responseType: 'blob',
  })
  const blob: Blob = resp.data
  const contentType: string =
    (resp.headers['content-type'] as string) ?? 'application/octet-stream'
  const url = URL.createObjectURL(blob)
  return { url, contentType }
}
