"""
15-agent-architecture: 企业级全栈 Agent 架构协同系统实战 (Full-Stack Agent System)

该模块将 12-FastAPI (接口网关/SSE流式)、13-SQLAlchemy (状态持久化/审计记账)、
14-Celery (异步任务解耦/长思考工作流) 与 LangGraph 状态机思想完整串联，
形成真正落地的企业级端到端 Agent 生产架构闭环。

架构全景：
  1. 用户发起高耗时 Agent 任务 -> FastAPI 接入层毫秒级响应，返回任务 task_id。
  2. 任务状态与元数据立即由 SQLAlchemy 异步 ORM 持久化至数据库 (状态: PENDING)。
  3. 后台异步执行集群 (Celery/Worker) 领取任务，执行多步推理状态机 (PLAN -> RETRIEVE -> SUMMARIZE)。
  4. 每一步执行轨迹与 Token 消耗实时落盘更新，并通过 SSE 流式总线推送到前端打字机。
  5. 前端即可轮询任务状态，亦可通过 SSE/WebSocket 获取毫秒级实时流。
"""

import asyncio
import json
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator, Dict, List, Optional

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# =====================================================================
# 一、 SQLAlchemy 2.0 异步持久化层：任务状态机与审计记账模型
# =====================================================================

DATABASE_URL = "sqlite+aiosqlite:///./enterprise_agent_audit.db"

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


class AgentTask(Base):
    """Agent 任务主表：追踪长任务生命周期与账单"""

    __tablename__ = "agent_tasks"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(50), default="enterprise_user_01")
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="PENDING"
    )  # PENDING, RUNNING, COMPLETED, FAILED
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )

    # 级联关联：一个任务包含多个子步骤轨迹 (Agent Steps)
    steps: Mapped[List["AgentStepLog"]] = relationship(
        "AgentStepLog", back_populates="task", cascade="all, delete-orphan"
    )


class AgentStepLog(Base):
    """Agent 思考轨迹明细表：记录 ReAct/LangGraph 每一步的节点与产物"""

    __tablename__ = "agent_step_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("agent_tasks.id"))
    step_name: Mapped[str] = mapped_column(
        String(50)
    )  # 如: PLAN, SEARCH, CRITIC, SUMMARY
    thought: Mapped[str] = mapped_column(Text)
    action: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    observation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    task: Mapped["AgentTask"] = relationship(
        "AgentTask", back_populates="steps"
    )


# 数据库依赖项
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


# =====================================================================
# 二、 实时事件总线 (SSE 广播机制，模拟端到端即时推流)
# =====================================================================


class TaskEventBus:
    """简单的事件总线，用于将后台 Worker 的思考过程实时推送给 SSE 客户端"""

    def __init__(self) -> None:
        self._listeners: Dict[str, List[asyncio.Queue]] = {}

    def subscribe(self, task_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        if task_id not in self._listeners:
            self._listeners[task_id] = []
        self._listeners[task_id].append(queue)
        return queue

    def unsubscribe(self, task_id: str, queue: asyncio.Queue) -> None:
        if task_id in self._listeners and queue in self._listeners[task_id]:
            self._listeners[task_id].remove(queue)
            if not self._listeners[task_id]:
                del self._listeners[task_id]

    async def publish(self, task_id: str, event_data: dict) -> None:
        if task_id in self._listeners:
            for queue in self._listeners[task_id]:
                await queue.put(event_data)


event_bus = TaskEventBus()

# =====================================================================
# 三、 后台异步 Agent 思考引擎 (模拟 Celery 分布式 Worker 与状态流转)
# =====================================================================


async def run_agent_workflow(task_id: str, prompt: str) -> None:
    """模拟在后台 Celery/异步 Worker 中运行的复杂 Multi-Agent 状态机流程

    完整执行：任务规划(PLAN) -> 多源搜索(SEARCH) -> 交叉验证(CRITIC) -> 研报生成(SUMMARY)
    """
    start_time = time.time()

    async with AsyncSessionLocal() as session:
        # 1. 状态流转为 RUNNING
        task_query = await session.execute(
            select(AgentTask).where(AgentTask.id == task_id)
        )
        task = task_query.scalar_one_or_none()
        if not task:
            return
        task.status = "RUNNING"
        await session.commit()

        await event_bus.publish(
            task_id,
            {"step": "STATUS_CHANGE", "status": "RUNNING", "message": "Agent 引擎启动，开始任务调度..."},
        )

        steps_definition = [
            (
                "PLAN",
                f"对需求 '{prompt}' 进行意图识别与子任务拆解",
                "Tool: TaskDecomposer",
                "生成 3 个子任务：数据挖掘、竞品对比、趋势研判",
                120,
            ),
            (
                "SEARCH",
                "调用搜索引擎与内部知识库进行全网检索",
                "Tool: HybridRAGSearch",
                "检索到 8 篇权威行业分析报告，置信度 0.92",
                280,
            ),
            (
                "CRITIC",
                "交叉校验检索事实，过滤营销噪声与幻觉",
                "Tool: FactVerifier",
                "校验通过，提炼出 5 条核心量化事实指标",
                160,
            ),
            (
                "SUMMARY",
                "整合推理链条，生成企业级深度分析报告",
                "Tool: ReportGenerator",
                f"【终极报告】针对 '{prompt}' 的战略研判：行业正在加速演进，基础设施与安全合规成为下半场竞争壁垒。",
                450,
            ),
        ]

        total_tokens = 0
        final_summary = ""

        for step_name, thought, action, observation, tokens in steps_definition:
            await asyncio.sleep(0.8)  # 模拟大模型思考推理耗时

            # 持久化单个步骤轨迹至数据库
            step_log = AgentStepLog(
                task_id=task_id,
                step_name=step_name,
                thought=thought,
                action=action,
                observation=observation,
            )
            session.add(step_log)
            total_tokens += tokens
            await session.commit()

            # 向 SSE 事件总线广播此步骤
            await event_bus.publish(
                task_id,
                {
                    "step": step_name,
                    "thought": thought,
                    "action": action,
                    "observation": observation,
                    "tokens_used": tokens,
                },
            )

            if step_name == "SUMMARY":
                final_summary = observation

        # 2. 状态流转为 COMPLETED
        duration = round(time.time() - start_time, 2)
        task.status = "COMPLETED"
        task.result = final_summary
        task.total_tokens = total_tokens
        task.duration_seconds = duration
        task.completed_at = datetime.utcnow()
        await session.commit()

        await event_bus.publish(
            task_id,
            {
                "step": "DONE",
                "status": "COMPLETED",
                "result": final_summary,
                "total_tokens": total_tokens,
                "duration_seconds": duration,
            },
        )


# =====================================================================
# 四、 FastAPI 高性能网关层：Lifespan 预热、接口定义与流式推流
# =====================================================================


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    # 启动时：初始化数据库表结构与预热连接池
    print(
        "\n🚀 [FastAPI Lifespan] 正在初始化企业级 Agent 持久化表结构 (SQLite/aiosqlite)..."
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ [FastAPI Lifespan] 数据库引擎就绪，Agent 全栈系统已启动！\n")

    yield

    # 关闭时：优雅释放连接池
    print("\n🛑 [FastAPI Lifespan] 正在安全释放数据库引擎连接池...")
    await engine.dispose()
    print("✅ [FastAPI Lifespan] 资源释放完毕。\n")


app = FastAPI(
    title="Enterprise Agent Full-Stack Architecture",
    description="整合 FastAPI + SQLAlchemy 异步 ORM + 异步任务队列的端到端 Agent 生产级架构",
    version="1.0.0",
    lifespan=lifespan,
)


class CreateTaskRequest(BaseModel):
    prompt: str = Field(
        ...,
        json_schema_extra={
            "example": "请分析 2026 年大模型工程化落地与 Agent 架构趋势"
        },
    )
    user_id: str = Field(default="admin_architect")


class CreateTaskResponse(BaseModel):
    task_id: str
    status: str
    message: str


@app.post("/api/tasks", response_model=CreateTaskResponse)
async def submit_agent_task(
    payload: CreateTaskRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """【端点 1：任务接入与解耦】

    接收复杂 Agent 任务，毫秒级持久化入库，并将耗时推理派发到后台异步任务，绝不阻塞当前 HTTP 连接。
    """
    new_task = AgentTask(
        prompt=payload.prompt,
        user_id=payload.user_id,
        status="PENDING",
    )
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)

    # 派发异步长任务（在生产中此处可替换为 celery_app.send_task）
    background_tasks.add_task(run_agent_workflow, new_task.id, payload.prompt)

    return CreateTaskResponse(
        task_id=new_task.id,
        status=new_task.status,
        message="任务已成功接收入库，后台 Agent 正在异步推理中，可通过 SSE 或轮询跟踪进度。",
    )


@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str, db: AsyncSession = Depends(get_db)):
    """【端点 2：任务状态与轨迹快照查询】

    支持根据 task_id 获取当前执行状态、全量步骤日志与 Token 审计账单。
    """
    query = await db.execute(
        select(AgentTask)
        .where(AgentTask.id == task_id)
        .options(
            # 使用 selectinload 预加载关联的思考步骤，彻底规避 N+1 查询
            # 从 sqlalchemy.orm 引入
        )
    )
    task = query.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="未找到指定的 Agent 任务")

    steps_query = await db.execute(
        select(AgentStepLog)
        .where(AgentStepLog.task_id == task_id)
        .order_by(AgentStepLog.id)
    )
    steps = steps_query.scalars().all()

    return {
        "task_id": task.id,
        "prompt": task.prompt,
        "status": task.status,
        "result": task.result,
        "total_tokens": task.total_tokens,
        "duration_seconds": task.duration_seconds,
        "created_at": task.created_at.isoformat(),
        "completed_at": (
            task.completed_at.isoformat() if task.completed_at else None
        ),
        "steps": [
            {
                "step_name": s.step_name,
                "thought": s.thought,
                "action": s.action,
                "observation": s.observation,
            }
            for s in steps
        ],
    }


@app.get("/api/tasks/{task_id}/stream")
async def stream_agent_steps(task_id: str):
    """【端点 3：SSE 实时打字机推流】

    通过 Server-Sent Events (SSE) 长连接，逐步实时推送 Agent 的思考状态机事件，客户端体验极致丝滑。
    """

    async def event_generator() -> AsyncGenerator[str, None]:
        queue = event_bus.subscribe(task_id)
        try:
            yield f"data: {json.dumps({'type': 'CONNECT', 'message': 'SSE 链路建立成功'}, ensure_ascii=False)}\n\n"

            while True:
                # 等待事件，带有超时防止僵尸连接
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                    if event.get("status") in ["COMPLETED", "FAILED"]:
                        break
                except asyncio.TimeoutError:
                    # 发送心跳包保活
                    yield ": ping\n\n"
        finally:
            event_bus.unsubscribe(task_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# =====================================================================
# 五、 开箱即用：终端自测交互客户端
# =====================================================================


async def run_standalone_demo() -> None:
    """无须开启独立服务器，直接在单进程内完整演示三者协同工作"""
    print("=" * 70)
    print("🌟 企业级全栈 Agent 架构端到端协同运行演示")
    print("=" * 70)

    # 1. 触发 Lifespan 初始化
    async with lifespan(app):
        # 2. 模拟客户端提交请求
        task_id = str(uuid.uuid4())
        prompt = "深度剖析 LangGraph 与 Celery 在企业生产环境下的分工与融合"
        print(f"📥 客户端提交新任务: '{prompt}'")

        async with AsyncSessionLocal() as session:
            task = AgentTask(id=task_id, prompt=prompt, status="PENDING")
            session.add(task)
            await session.commit()
            print(f"💾 [SQLAlchemy] 任务已持久化入库，生成唯一 task_id: {task_id}")

        # 3. 开启后台异步推理并在终端实时监听流式输出
        print("\n🚀 [后台 Worker 启动] 开始多阶段状态机推理 (实时广播流):")

        queue = event_bus.subscribe(task_id)

        # 启动工作协程
        worker_task = asyncio.create_task(run_agent_workflow(task_id, prompt))

        # 消费 SSE 流并打印到控制台
        while True:
            event = await queue.get()
            step_type = event.get("step")
            if step_type == "STATUS_CHANGE":
                print(f"  ⚡ 状态更新 -> {event['status']}: {event['message']}")
            elif step_type in ["PLAN", "SEARCH", "CRITIC", "SUMMARY"]:
                print(f"  🧠 [步骤 {step_type}]")
                print(f"     思考: {event['thought']}")
                print(f"     动作: {event['action']}")
                print(f"     产出: {event['observation'][:60]}...")
                print(f"     Token 消耗: +{event['tokens_used']} tokens")
            elif step_type == "DONE":
                print(
                    f"\n🎉 [任务完成] 总耗时: {event['duration_seconds']} 秒 | 累计 Token: {event['total_tokens']}"
                )
                print(f"🏆 最终产出: {event['result']}")
                break

        await worker_task
        event_bus.unsubscribe(task_id, queue)

        # 4. 从数据库回读验证持久化数据
        print("\n🔍 [数据库回读验证] 查询持久化记录与步骤日志明细:")
        async with AsyncSessionLocal() as session:
            q = await session.execute(
                select(AgentTask).where(AgentTask.id == task_id)
            )
            saved_task = q.scalar_one()
            steps_q = await session.execute(
                select(AgentStepLog).where(AgentStepLog.task_id == task_id)
            )
            saved_steps = steps_q.scalars().all()

            print(
                f"   数据库主表状态: {saved_task.status} | 计费 Tokens: {saved_task.total_tokens}"
            )
            print(f"   数据库子表包含步骤记录数: {len(saved_steps)} 条")
            for idx, s in enumerate(saved_steps, 1):
                print(f"     步骤 {idx}: [{s.step_name}] -> {s.thought}")

    print("\n" + "=" * 70)
    print("✅ 演示完毕！12-FastAPI + 13-SQLAlchemy + 14-Celery + 状态机闭环完全成功！")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_standalone_demo())
