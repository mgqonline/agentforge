# 15-agent-architecture · 企业级全栈 Agent 架构协同实战

## 🎯 核心目标与应用场景

**核心目标**：跳出单脚本与单机玩具，将 **12-FastAPI (接口网关/SSE流式)**、**13-SQLAlchemy (状态持久化/审计记账)**、**14-Celery (异步任务解耦/长思考工作流)** 与 **LangGraph 状态机** 融会贯通，构建高可用、可观测、可水平扩展的企业级生产架构闭环。

**为什么必须将 12-15 融合成完整体系**：
许多初学者困惑：“为什么 AI 教程要学 FastAPI、SQLAlchemy 和 Celery？是不是在灌水重复装依赖？”
**答案是：这是玩具 Demo 与企业级 AI 系统的分水岭！**
- 单纯的 LangChain/LangGraph 代码只能在控制台打印 `print()`；
- 真实生产中，一次复杂的深度研报或 Multi-Agent 协作可能需要思考数分钟：
  - 如果没有 **FastAPI**，就无法提供毫秒级任务接入与实时 SSE 打字机流式推流；
  - 如果没有 **SQLAlchemy**，一旦服务器断电或重启，Agent 所有的思考轨迹、记忆与 Token 账单将全部丢失；
  - 如果没有 **Celery** 异步解耦，长耗时推理会导致 HTTP 连接直接超时（504 崩溃），且无法应对外部大模型频繁的 429 限流雪崩。
第 15 章正是这三者的**集大成实战之地**。

**真实应用场景**：
1. **企业级异步研报智能体平台**：用户提交深度分析需求，系统毫秒级返回 `task_id`，后台 Worker 集群自动运行多步状态机，前端实时 SSE 接收打字机推流，数据库全程审计。
2. **多租户 Agent 运行轨迹与 Token 账单中心**：精确记录每次 Tool 调用耗时、每个节点的输入输出、以及按用户/按会话的 Token 消耗，满足企业财务记账与合规审计要求。
3. **断点续传与人机协同 (HITL) 生产网关**：当 Agent 遇到敏感高风险操作（如退款、删库）时，状态机持久化挂起为 `WAITING_APPROVAL`，审批人通过 Web 接口审批后，后台 Worker 恢复执行。

---

## 🧠 技术原理与架构流程图

本模块实现了一个真正的端到端企业级 Agent 生产协同架构：

```mermaid
flowchart TD
    User([前端客户端 / Web 页面]) -->|1. POST /api/tasks 发起任务| API[12-FastAPI 高性能接入层]
    API -->|2. 毫秒级写入状态 PENDING| DB[(13-SQLAlchemy 异步持久化层<br>SQLite / PostgreSQL)]
    API -.->|3. 立即返回 task_id| User
    
    API -->|4. 派发后台任务| Queue[(14-Celery / 后台 Worker 队列)]
    
    subgraph 核心状态机推理集群 (LangGraph Engine)
        Queue --> W[异步 Agent Worker]
        W --> S1[阶段一: PLAN 意图与任务拆解]
        S1 --> S2[阶段二: SEARCH 多源检索]
        S2 --> S3[阶段三: CRITIC 事实交叉校验]
        S3 --> S4[阶段四: SUMMARY 终极研报合成]
    end
    
    W -->|5. 每步思考轨迹实时落盘| DB
    W -->|6. 发布步骤事件| Bus[SSE 实时广播总线]
    Bus -->|7. GET /api/tasks/{task_id}/stream 实时打字机推流| User
    
    User -->|8. GET /api/tasks/{task_id} 轮询回读完整轨迹| API
    API -->|从数据库聚合加载| DB
```

**原理解析**：
1. **接入与计算彻底解耦**：FastAPI 绝不直接同步执行大模型推理，而是充当“接待前台与流式派发器”，耗时工作交由后台 Worker 消费，保障网关万级吞吐能力。
2. **任务与步骤两级 ORM 建模**：
   - `AgentTask`（主表）：追踪任务整体状态（`PENDING` -> `RUNNING` -> `COMPLETED` / `FAILED`）、累计耗时与总 Token 消耗。
   - `AgentStepLog`（明细表）：记录每个状态节点（`PLAN`, `SEARCH`, `CRITIC`, `SUMMARY`）的输入、输出、Tool 名称与局部 Token，支持全链路回溯。
3. **SSE 实时流与持久化双通道同步**：Worker 在完成每一步推理时，同时向数据库提交事务（确保持久性）并向事件总线广播（确保前端低延迟体验）。

---

## 🛠️ 操作方法与执行命令

本章节包含单脚本自测演示与标准分布式服务化部署两种模式：

### 模式一：开箱即用单脚本演示（推荐首选）

无需配置复杂的外部服务，直接运行即可在终端看到完整的“任务接入 -> 数据库落盘 -> Worker异步推理 -> SSE实时流 -> 数据库回读验证”全生命周期：

```bash
# 1. 激活虚拟环境
source venv/bin/activate

# 2. 直接运行全栈端到端实战脚本
python 15-agent-architecture/full_stack_agent_system.py
```

### 模式二：作为独立 API 微服务运行与交互测试

```bash
# 1. 启动企业级 Agent FastAPI 接口服务
uvicorn 15-agent-architecture.full_stack_agent_system:app --reload --port 8090

# 2. 在新终端提交一个复杂的 Agent 任务
curl -X POST http://127.0.0.1:8090/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"prompt": "分析大模型工程化落地趋势", "user_id": "architect_01"}'
# 记录返回的 task_id，例如: 867f9723-fbb4-43c6-874f-cb9d5eeb4f7f

# 3. 通过 SSE 实时打字机订阅 Agent 推理步骤（实时推流）
curl -N http://127.0.0.1:8090/api/tasks/<填入你的task_id>/stream

# 4. 任务完成后，回读数据库中的完整轨迹快照与账单明细
curl http://127.0.0.1:8090/api/tasks/<填入你的task_id>
```

### 模式三：阅读企业级架构白皮书

```bash
# 深入研读企业落地硬性指标与三大死亡难点解决方案
cat 15-agent-architecture/ENTERPRISE_AGENT_WHITEPAPER.md
```

---

## ⚠️ 注意事项与踩坑记录

1. **SQLAlchemy 异步模式下的 greenlet 缺失报错**：
   - 报错：`ValueError: the greenlet library is required to use this function`
   - 原因：SQLAlchemy 异步扩展依赖 `greenlet` 实现协程与 C 扩展切换。
   - 解决方案：运行 `pip install greenlet`。
2. **长连接保活与代理超时 (X-Accel-Buffering)**：
   - 在生产环境经过 Nginx 反向代理时，Nginx 默认会开启响应缓冲（Buffer），导致 SSE 流式输出变成“卡顿5秒后一口气全部吐出”。
   - 解决方案：在 FastAPI 的 SSE 响应头中必须显式添加 `"X-Accel-Buffering": "no"`，并在客户端断链时由 `event_generator` 自动注销队列监听器，防止内存泄漏。
3. **大模型任务异步执行中的数据库会话隔离**：
   - 严禁在主请求协程与后台 Worker 协程之间传递同一个 `AsyncSession`。Worker 必须拥有自己独立的 `async with AsyncSessionLocal() as session:` 上下文。