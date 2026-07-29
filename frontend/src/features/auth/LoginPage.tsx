import { useState } from 'react'
import { Card, Form, Input, Button, Typography, message } from 'antd'
import { useNavigate } from 'react-router-dom'
import { authApi } from '@/lib/api/client'
import { useAuth } from '@/store/auth'
import type { LoginRequest } from '@/types'

const { Title, Paragraph } = Typography

export default function LoginPage() {
  const navigate = useNavigate()
  const login = useAuth((s) => s.login)
  const [loading, setLoading] = useState(false)

  const onFinish = async (values: LoginRequest) => {
    setLoading(true)
    try {
      const res = await authApi.login(values)
      login(res.access_token, res.user)
      message.success('登录成功')
      navigate('/workspace')
    } catch {
      message.error('登录失败,请检查用户名和密码')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        background: '#f0f2f5',
      }}
    >
      <Card style={{ width: 380 }}>
        <Title level={3} style={{ textAlign: 'center', marginBottom: 24 }}>
          线束工艺辅助卡系统
        </Title>
        <Form
          layout="vertical"
          onFinish={onFinish}
          initialValues={{ name: '', password: '' }}
        >
          <Form.Item
            label="用户名"
            name="name"
            rules={[{ required: true, message: '请输入用户名' }]}
          >
            <Input placeholder="请输入用户名" autoComplete="username" />
          </Form.Item>
          <Form.Item
            label="密码"
            name="password"
            rules={[{ required: true, message: '请输入密码' }]}
          >
            <Input.Password placeholder="请输入密码" autoComplete="current-password" />
          </Form.Item>
          <Form.Item style={{ marginBottom: 8 }}>
            <Button type="primary" htmlType="submit" block loading={loading}>
              登录
            </Button>
          </Form.Item>
        </Form>
        <Paragraph type="secondary" style={{ textAlign: 'center', marginBottom: 0 }}>
          默认账号:admin / admin
        </Paragraph>
      </Card>
    </div>
  )
}
