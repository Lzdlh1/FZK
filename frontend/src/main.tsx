import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import App from './App'

const queryClient = new QueryClient()

// 注意:不使用 React.StrictMode。Univer 在 dev 下不兼容 StrictMode 的双挂载
// (dispose 不彻底,二次挂载触发 "Injector cannot be accessed after it was disposed"),
// 会导致表格无法渲染。
ReactDOM.createRoot(document.getElementById('root')!).render(
  <QueryClientProvider client={queryClient}>
    <ConfigProvider locale={zhCN}>
      <App />
    </ConfigProvider>
  </QueryClientProvider>
)
