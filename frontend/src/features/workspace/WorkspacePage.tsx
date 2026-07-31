import { Layout, Card, Button, Space, Typography, Row, Col } from 'antd'
import { SettingOutlined, DatabaseOutlined } from '@ant-design/icons'
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
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} md={8}>
            <Card
              title="新建解析任务"
              hoverable
              onClick={() => navigate('/workspace/new')}
              style={{ height: '100%' }}
            >
              <Text type="secondary">
                上传图纸并选择模板,自动识别线束参数。
              </Text>
            </Card>
          </Col>
          <Col xs={24} sm={12} md={8}>
            <Card
              title="任务列表"
              hoverable
              onClick={() => navigate('/parse-jobs')}
              style={{ height: '100%' }}
            >
              <Text type="secondary">
                查看历史解析任务,进入审核工作台校对识别结果。
              </Text>
            </Card>
          </Col>
          <Col xs={24} sm={12} md={8}>
            <Card
              title="前往模板设计"
              hoverable
              onClick={() => navigate('/templates')}
              style={{ height: '100%' }}
            >
              <Text type="secondary">管理变量模板与公式定义。</Text>
            </Card>
          </Col>
          <Col xs={24} sm={12} md={8}>
            <Card
              title={
                <Space>
                  <DatabaseOutlined />
                  数据库参数
                </Space>
              }
              hoverable
              onClick={() => navigate('/database-params')}
              style={{ height: '100%' }}
            >
              <Text type="secondary">
                管理线束参数库，支持 Excel 批量导入导出。
              </Text>
            </Card>
          </Col>
          <Col xs={24} sm={12} md={8}>
            <Card
              title={
                <Space>
                  <SettingOutlined />
                  系统设置
                </Space>
              }
              hoverable
              onClick={() => navigate('/settings')}
              style={{ height: '100%' }}
            >
              <Text type="secondary">
                配置 AI 供应商、API Key、模型型号。
              </Text>
            </Card>
          </Col>
        </Row>
      </Content>
    </Layout>
  )
}
