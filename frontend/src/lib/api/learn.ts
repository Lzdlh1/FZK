import client from './client'
import type {
  LearnSampleCreate,
  LearnSampleOut,
  LearnTryResponse,
} from '@/types'

export const learnApi = {
  /** 上传示例图纸并让 AI 尝试解析(不创建解析任务) */
  tryParse(
    templateId: string,
    file: File,
    drawingName?: string
  ): Promise<LearnTryResponse> {
    const form = new FormData()
    form.append('drawing', file)
    form.append('template_id', templateId)
    if (drawingName) form.append('drawing_name', drawingName)
    return client
      .post<LearnTryResponse>('/learn/try', form, { timeout: 180000 })
      .then((res) => res.data)
  },

  /** 某模板的训练样本列表(最新在前) */
  listSamples(templateId: string): Promise<LearnSampleOut[]> {
    return client
      .get<LearnSampleOut[]>('/learn/samples', {
        params: { template_id: templateId },
      })
      .then((res) => res.data)
  },

  /** 保存一条训练样本(纠正后的期望结果) */
  createSample(body: LearnSampleCreate): Promise<LearnSampleOut> {
    return client.post<LearnSampleOut>('/learn/samples', body).then((res) => res.data)
  },

  /** 删除样本(连同存储中的示例图纸) */
  deleteSample(id: string): Promise<void> {
    return client.delete(`/learn/samples/${id}`).then(() => undefined)
  },

  /** 加载样本图纸为 ObjectURL(接口需鉴权,故以 blob 形式拉取) */
  async loadSampleImage(id: string): Promise<string> {
    const resp = await client.get(`/learn/samples/${id}/image`, {
      responseType: 'blob',
    })
    return URL.createObjectURL(resp.data as Blob)
  },
}
