import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from 'axios'
import { useAuth } from '@/store/auth'
import type { LoginRequest, LoginResponse } from '@/types'

const client: AxiosInstance = axios.create({
  baseURL: '/api',
  // AI 解析可能耗时较长(模型响应 30-60s+),全局放宽到 120s;
  // 长任务(如 run)在调用处再用更长的 timeout 覆盖。
  timeout: 120000,
})

// 请求拦截器:自动携带 JWT
client.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = useAuth.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器:401 清 token 并跳登录
client.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status
    if (status === 401) {
      useAuth.getState().logout()
      if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export const authApi = {
  login(data: LoginRequest): Promise<LoginResponse> {
    return client.post<LoginResponse>('/auth/login', data).then((res) => res.data)
  },
}

export default client
