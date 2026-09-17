# 🚀 AgentForge · 产品交付落地与工程推进路线图 (Delivery Roadmap)

> **文档性质**：生产交付标准、待推进工程清单与版本演进排期  
> **面向对象**：研发负责人、项目交付经理、企业实施架构师

---

## 📌 一、 交付成熟度现状评估 (Delivery Readiness Status)

| 交付维度 | 当前成熟度 | 已就绪能力 (Delivered) | 本次攻坚完成项 (Just Finished) | 待后续推进项 (In Progress) |
| :--- | :---: | :--- | :--- | :--- |
| **1. 核心架构闭环** | **98%** | 01-23 阶段完整代码、LangGraph 状态机、Hybrid RAG | 交付 15 章全栈协同系统 `full_stack_agent_system.py` | 接入分布式大规模 Swarm 拓扑 |
| **2. 工具链与 DX** | **95%** | 一键启动脚本 `start_services.sh` | 交付官方 CLI 工具 `scripts/agentforge_cli.py` (doctor/run/test/poc) | 发布为 PyPI 全局命令 `agentforge` |
| **3. 生产打包部署** | **95%** | 原有基础开发版 docker-compose | 交付企业生产版 `docker-compose.prod.yml` 与运维 SOP 指南 | 编写 K8s / Helm Chart 编排模板 |
| **4. 质量与测试** | **95%** | 单章节集成测试用例 | 交付 `tests/test_e2e_smoke.py` (9项全绿) + GitHub Actions CI 流水线 | 接入自动化压测与 Ragas 真实性基准评测 |
| **5. 前后端融合** | **85%** | React 18 终端、Monaco 代码沙箱、SSE 打字机 | 标准化 OpenAPI 3.0 规范 `docs/OPENAPI_SPEC.json` | 彻底归档旧版 Vanilla JS 前端目录 |
| **6. 安全与企业合规** | **95%** | AST 语法树审查、HITL 人机审批中断点 | 多租户 JWT/RBAC、滑动窗口限流 (`auth_governance.py`) + 安全沙箱 (`security_sandbox.py`) | 接入外部 E2B MicroVM 硬件级隔离 |

---

## 🎯 二、 详细待推进清单与责任人分工

### 阶段一：工程收敛与标准化（已完成）

- [x] **任务 1.1**：编写官方 CLI 工具 (`scripts/agentforge_cli.py`)，支持一键 `doctor` 体检、`run <chapter>`、`test` 冒烟自检。
- [x] **任务 1.2**：交付生产级一键全栈容器编排清单 (`docker-compose.prod.yml`)，覆盖 Postgres、Redis、FastAPI 网关与 Celery Worker。
- [x] **任务 1.3**：编写全局全栈冒烟测试套件 (`tests/test_e2e_smoke.py`)，实现零依赖 0.5 秒极速确定性校验。
- [ ] **任务 1.4**：清理并收敛前端代码库，将 `frontend-react` 设为唯一标准 Web UI，归档旧版 `frontend/`。
- [ ] **任务 1.5**：采用 `uv` 或 `poetry` 生成全局唯一的锁版本依赖文件 (`uv.lock`)，消除跨机器 pip 安装时的子依赖冲突。

---

### 阶段二：企业级安全、鉴权与质量护栏（已完成）

- [x] **任务 2.1：真实多租户 RBAC 与 JWT 鉴权中枢** (`backend/auth_governance.py`)
  - 实现基于 HMAC-SHA256 签名算法的零外部依赖 JWT 引擎（Base64URL 编码）；
  - 实现内存/Redis 兼容的滑动时间窗口 QPS 速率限制器；
  - 落地基于 Token 预算的消耗追踪与自动熔断拦截器。
- [x] **任务 2.2：代码执行沙箱安全加固 (Sandbox Hardening)** (`backend/security_sandbox.py`)
  - 强化 Python AST 抽象语法树审查，拦截 `os`, `sys`, `subprocess` 等危险模块；
  - 拦截 `__subclasses__` 等沙箱逃逸属性，并加入 3 秒超时守护子进程，有效阻断死循环。
- [x] **任务 2.3：CI/CD 自动化回归流水线** (`.github/workflows/ci.yml`)
  - 配置 GitHub Actions PR 自动化门禁，覆盖 Python 3.10 与 3.11 多版本矩阵；
  - 自动化执行安全审计与 `tests/test_e2e_smoke.py` 冒烟测试套件。

---

### 阶段三：商业化实施与客户交付赋能（已完成）

- [x] **任务 3.1：编写《企业私有化部署与高可用运维手册》** (`docs/ENTERPRISE_DEPLOYMENT_SOP.md`)
  - 详尽阐述冷启动预热流程、PostgreSQL 主从备份、Redis 容灾策略；
  - 提供 7B/14B/32B 硬件配置选型指南（显存/内存容量精细速查表）。
- [x] **任务 3.2：标准化 OpenAPI 3.0 / Swagger 接口契约** (`docs/OPENAPI_SPEC.json`)
  - 制定规范的 RESTful API 协议，包含异步任务提交、SSE 事件流订阅、任务状态轮询与 Token 消耗审计。
- [x] **任务 3.3：封装 POC (概念验证) 演示大礼包** (`scripts/run_enterprise_poc.py`)
  - 内置企业财报混合检索、合同结构化提取、多模态图表解析模拟流水线；
  - 现场一键输出 5 项量化指标评估报告（检索召回率、意图识别准确率、Token 节约率等）；
  - 深度集成进 CLI：`python scripts/agentforge_cli.py poc`。

---

## 💡 交付验收准则 (Acceptance Criteria)

1. **开箱即跑 (Out-of-the-Box)**：任何一台纯净电脑（macOS / Linux / Windows），执行 `python scripts/agentforge_cli.py doctor` 显示全绿，运行任一章节无需修改源码。
2. **生产高可用 (High Availability)**：在外部大模型报 429 限流或网络抖动时，系统自动指数退避重试，无异常抛出，HTTP 连接绝不超时。
3. **安全合规 (Zero Risk)**：所有涉及修改数据库、执行 Shell 命令的危险动作，百分之百受 HITL 审批阻断或沙箱隔离保护。
