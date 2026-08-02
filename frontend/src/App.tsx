import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Result, Button } from 'antd'
import LoginPage from '@/features/auth/LoginPage'
import ProtectedRoute from '@/features/auth/ProtectedRoute'
import WorkspacePage from '@/features/workspace/WorkspacePage'
import ParseJobsListPage from '@/features/workspace/ParseJobsListPage'
import NewParseJobPage from '@/features/workspace/NewParseJobPage'
import ReviewPage from '@/features/workspace/ReviewPage'
import TemplateListPage from '@/features/designer/TemplateListPage'
import DesignerPage from '@/features/designer/DesignerPage'
import SettingsPage from '@/features/settings/SettingsPage'
import DatabaseParamsPage from '@/features/database/DatabaseParamsPage'
import RulesPage from '@/features/rules/RulesPage'
import LearnPage from '@/features/learn/LearnPage'

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
          <Route path="/workspace/new" element={<NewParseJobPage />} />
          <Route path="/parse-jobs" element={<ParseJobsListPage />} />
          <Route path="/parse-jobs/:id/review" element={<ReviewPage />} />
          <Route path="/templates" element={<TemplateListPage />} />
          <Route path="/designer" element={<DesignerPage />} />
          <Route path="/designer/:templateId" element={<DesignerPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/database-params" element={<DatabaseParamsPage />} />
          <Route path="/rules" element={<RulesPage />} />
          <Route path="/learn" element={<LearnPage />} />
        </Route>
        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
