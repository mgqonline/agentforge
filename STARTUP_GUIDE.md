# AgentForge 服务启动指南

AgentForge 采用前后端分离架构，唯一标准 Web 前端为 `frontend-react/`。旧版 `frontend/` 已移除，不再提供 Vanilla JS 兼容入口。

## 服务清单

| 服务 | 默认地址 | 作用 |
| --- | --- | --- |
| PostgreSQL | `localhost:5432` | 任务、会话、治理和审计数据持久化 |
| Redis | `localhost:6380`（本地 Compose） | 缓存、限流和任务队列 |
| FastAPI | `http://localhost:6001` | AI Agent、课程、知识库和评测 API |
| React 工作台 | `http://localhost:6000` | 学习关卡、对话、代码提交和结果展示 |

## 本地启动

### 1. 准备环境变量

```bash
cp .env.example .env
# 编辑 .env，至少填写 POSTGRES_PASSWORD、JWT_SECRET 和模型 API 配置
```

### 2. 启动后端依赖

```bash
docker compose up -d postgres redis
```

### 3. 启动后端

```bash
source venv/bin/activate
cd backend
uvicorn main:app --host 0.0.0.0 --port 6001 --reload --ws-max-size 104857600
```

### 4. 启动 React 前端

```bash
cd frontend-react
npm ci
npm run dev -- --host 0.0.0.0 --port 6000
```

打开 `http://localhost:6000/` 验证工作台。

## 一键启动

```bash
scripts/start_services.sh
```

脚本会启动 PostgreSQL、Redis、FastAPI 和 `frontend-react`，并等待后端与 React 前端可以访问。可使用以下命令查看或停止服务：

```bash
scripts/start_services.sh --status
scripts/start_services.sh --stop
```

## 生产构建

生产 Compose 使用 `frontend-react/Dockerfile` 构建 React 静态资源，并由 Nginx 提供单一前端入口：

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

生产环境必须通过 `.env` 提供强密码、`JWT_SECRET`、模型 API Key 和明确的 `ALLOWED_ORIGINS`，不要依赖 Compose 默认值。

## 质量验证

```bash
python3 -m py_compile backend/*.py
python3 tests/test_e2e_smoke.py
python3 backend/auth_governance.py
python3 backend/security_sandbox.py
cd frontend-react && npm run lint && npm run build
```