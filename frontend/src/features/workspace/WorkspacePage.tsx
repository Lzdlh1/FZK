import { Layout, Card, Button, Space, Typography } from 'antd'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/store/auth'

const { Header, Content } = Layout
const { Title, Text } = Typography

export default function WorkspacePage() {
  const navigate = useNavigate()
  const user = useAuth((s) => s.user)
  const logout = useAuth((s) => s.logout)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          background: '#fff',
          padding: '0 24px',
          borderBottom: '1px solid #f0f0f0',
        }}
      >
        <Title level={4} style={{ margin: 0 }}>
          线束工艺辅助卡系统
        </Title>
        <Space>
          <Text>当前用户:{user?.name ?? '未知'}</Text>
          <Button onClick={handleLogout}>登出</Button>
        </Space>
      </Header>
      <Content style={{ padding: 24 }}>
        <Card>
          <Title level={3}>工艺卡工作台 - 待实现(1b 阶段)</Title>
          <Text type="secondary">该页面将在 1b 阶段实现具体功能。</Text>
        </Card>
      </Content>
    </Layout>
  )
}
