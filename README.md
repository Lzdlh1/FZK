# FZK — 线束工艺辅助卡系统

基于 AI 的线束图纸智能解析工具：上传线束图纸，自动抽取工艺参数，经人工审核后生成 Excel 工艺辅助卡。

## 技术栈

- 后端：FastAPI + SQLAlchemy + AI 网关（OpenAI 兼容多 Provider 路由）
- 前端：React 18 + TypeScript + Vite + Ant Design + Univer 表格
- 存储：PostgreSQL / SQLite + MinIO 对象存储
- 部署：Docker Compose、PyInstaller 桌面打包

## 目录结构

- `backend/` — FastAPI 后端：解析管线（格式分流 / AI 抽取 / 后处理）、公式引擎、AI 网关、输出生成
- `frontend/` — React 前端：工作台、模板设计器、审核工作台、系统设置
- `docker-compose.yml` — Postgres + MinIO + 后端 + 前端一键部署

## 快速开始

```bash
docker compose up -d
```

本地开发：

```bash
# 后端
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload

# 前端
cd frontend && pnpm install && pnpm dev
```

默认管理员账号：admin / admin（首次启动自动创建）。