import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Result, Button } from 'antd'
import LoginPage from '@/features/auth/LoginPage'
import ProtectedRoute from '@/features/auth/ProtectedRoute'
import WorkspacePage from '@/features/workspace/WorkspacePage'

function NotFound() {
  return (
    <Result
      status="404"
      title="404"
      subTitle="抱歉,您访问的页面不存在。"
      extra={
        <Button type="primary" href="/workspace">
          返回工作台
        </Button>
      }
    />
  )
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<ProtectedRoute />}>
          <Route path="/" element={<Navigate to="/workspace" replace />} />
          <Route path="/workspace" element={<WorkspacePage />} />
        </Route>
        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
