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
