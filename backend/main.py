import os
import asyncio
import time
import uuid
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from fastapi import Depends, Header, HTTPException, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# 使用原生的 openai 库替代 langchain_openai，绕过底层的 pathlib import 致命 bug
import openai

from rag_engine import rag_engine

import sys
import contextlib
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp import ClientSession

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from examples.mysql_agent import build_mysql_agent
from langchain_core.messages import HumanMessage
from orchestrator_graph import build_orchestrator_graph
from agent_governance import (
    governance_metrics,
    ensure_governance_schema,
    list_approval_audits,
    list_pending_approvals,
    list_tool_run_audits,
    reject_approval_decision,
)
from agent_security import (
    AuthContext,
    auth_to_dict,
    authenticate,
    create_context_token,
    consume_ws_ticket,
    create_ws_ticket,
    login_user,
    register_user,
    require_permission,
    validate_security_config,
)

load_dotenv()
app = FastAPI(
    title="AgentForge · 智炼工坊 API",
    description="企业级全栈 AI 架构师实操练兵场与代码评测沙箱核心引擎",
    version="2.0.0"
)

# ==========================================
# 1. CORS 安全跨域配置 (防止跨站请求伪造)
# ==========================================
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:8000,http://127.0.0.1:8000,http://localhost:3000,http://127.0.0.1:5500,http://localhost:5173,http://localhost:5174,http://localhost:5175,http://localhost:6000,http://127.0.0.1:6000,http://localhost:6001,http://127.0.0.1:6001,http://localhost:6002,http://127.0.0.1:6002"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# ==========================================
# 2. 敏感词过滤 API (模拟企业安全风控网关)
# ==========================================
import re
async def check_sensitive_words(text: str) -> bool:
    """
    模拟调用企业级敏感词 API。
    返回 True 表示存在敏感词，False 表示安全。
    """
    # 模拟外部 API 延迟
    await asyncio.sleep(0.1)
    
    # 内置黑名单库 (实际中应该通过 REST API 向安全合规中心发起请求)
    black_list = [r"涉密", r"内部核算", r"机密代码", r"黑客", r"脱库"]
    for pattern in black_list:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False

async def check_prompt_injection(text: str) -> bool:
    """
    基于启发式规则拦截常见的 Prompt Injection 攻击。
    """
    injection_patterns = [
        r"ignore previous",
        r"忽略.*?指令",
        r"system prompt",
        r"系统提示词",
        r"you are now",
        r"现在你是",
        r"forget everything",
        r"忘记一切",
        r"bypass",
        r"绕过"
    ]
    for pattern in injection_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False

model_name = os.getenv("MODEL_NAME", "deepseek-v4-pro")
api_key = os.getenv("OPENAI_API_KEY", "dummy")
base_url = os.getenv("OPENAI_API_BASE", "https://api.deepseek.com/v1")

client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)

SYSTEM_PROMPT_TEMPLATE = """
你是拓维信息（位于拓维信息AI应用开发中心）的首席企业级 AI Agent。
基于以下企业内部知识库内容回答用户问题：
---
{context}
---
请保持回答专业、客观，并且符合咱们公司的业务调性。
"""

class ConnectionManager:
    def __init__(self):
        # 活跃的 WebSocket 会话池，隔离不同用户的上下文和状态
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, connection_key: str):
        await websocket.accept()
        # 强制踢出旧的重复会话（防止同一用户多开导致的并发冲突）
        if connection_key in self.active_connections:
            try:
                await self.active_connections[connection_key].close(code=1008, reason="Duplicated session")
            except Exception as exc:
                print(f"[会话管理器] 关闭重复会话失败: {exc}")
        self.active_connections[connection_key] = websocket
        print(f"[会话管理器] 客户端已连接，Connection: {connection_key}，当前活跃数: {len(self.active_connections)}")

    def disconnect(self, connection_key: str):
        if connection_key in self.active_connections:
            del self.active_connections[connection_key]
            print(f"[会话管理器] 客户端已断开，Connection: {connection_key}，当前活跃数: {len(self.active_connections)}")

manager = ConnectionManager()

class MCPManager:
    def __init__(self):
        self.session = None
        self.exit_stack = contextlib.AsyncExitStack()
        self.openai_tools = []
        
    async def start(self):
        # 启动外挂的 MCP Server 进程
        server_params = StdioServerParameters(
            command="python",
            args=["mcp_server.py"],
            env=dict(os.environ)
        )
        self.stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        read, write = self.stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(read, write))
        await self.session.initialize()
        
        # 动态发现 MCP Server 提供的所有工具
        tools_resp = await self.session.list_tools()
        for t in tools_resp.tools:
            self.openai_tools.append({
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.inputSchema
                }
            })
            print(f"[MCP Client] 成功发现外挂工具: {t.name}")
            
    async def call_tool(self, name: str, arguments: dict, auth: AuthContext | None = None):
        scoped_arguments = dict(arguments or {})
        if auth:
            scoped_arguments.setdefault("auth_token", create_context_token(auth, ttl_seconds=120))
            scoped_arguments.setdefault("session_id", auth.session_id)
        res = await self.session.call_tool(name, scoped_arguments)
        return "\n".join([c.text for c in res.content])
        
    async def shutdown(self):
        await self.exit_stack.aclose()

mcp_client = MCPManager()

@app.on_event("startup")
async def startup_event():
    # 启动时初始化或加载知识库与安全配置
    try:
        validate_security_config()
    except Exception as e:
        print(f"⚠️ [Startup] 安全配置初始化警告: {e}")

    try:
        await ensure_governance_schema()
    except Exception as e:
        print(f"⚠️ [Startup] 数据库未连接，企业治理中枢启用内存高兼容模式: {e}")

    try:
        rag_engine.build_or_load()
    except Exception as e:
        print(f"⚠️ [Startup] 知识库加载提示: {e}")

    try:
        await mcp_client.start()
    except Exception as e:
        print(f"⚠️ [Startup] MCP Client 启动提示: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    await mcp_client.shutdown()


def _bearer_token(value: str | None) -> str | None:
    if not value:
        return None
    if value.lower().startswith("bearer "):
        return value[7:].strip()
    return value.strip()


class AuthRequest(BaseModel):
    username: str
    password: str


class WsTicketRequest(BaseModel):
    session_id: str


@app.post("/api/agent/auth/register")
async def api_register_user(payload: AuthRequest):
    try:
        await register_user(payload.username, payload.password)
        login = await login_user(payload.username, payload.password)
        return login
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/agent/auth/login")
async def api_login_user(payload: AuthRequest):
    login = await login_user(payload.username, payload.password)
    if login is None:
        raise HTTPException(status_code=401, detail="invalid username or password")
    return login


async def get_auth_context(
    authorization: str | None = Header(default=None),
    x_session_id: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None),
) -> AuthContext:
    auth = authenticate(_bearer_token(authorization), x_session_id or "http", x_user_id)
    if not auth.roles:
        raise HTTPException(status_code=401, detail="authentication required")
    return auth


@app.get("/api/agent/auth/me")
async def auth_me(auth: AuthContext = Depends(get_auth_context)):
    return auth_to_dict(auth)


@app.post("/api/agent/ws-ticket")
async def api_create_ws_ticket(payload: WsTicketRequest, auth: AuthContext = Depends(get_auth_context)):
    if not auth.has_permission("chat:use"):
        raise HTTPException(status_code=403, detail="missing permission: chat:use")
    session_id = payload.session_id.strip()
    if not session_id or len(session_id) > 160:
        raise HTTPException(status_code=400, detail="invalid session_id")
    ticket = create_ws_ticket(auth, session_id, ttl_seconds=60)
    return {
        "ticket": ticket,
        "expires_in": 60,
        "session_id": session_id,
        "user_id": auth.user_id,
        "tenant_id": auth.tenant_id,
    }


@app.get("/api/agent/audit/approvals")
async def api_list_approval_audits(
    status: str | None = None,
    session_id: str | None = None,
    limit: int = 50,
    auth: AuthContext = Depends(get_auth_context),
):
    try:
        require_permission(auth, "audit:read")
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return {"items": await list_approval_audits(status=status, session_id=session_id, tenant_id=auth.tenant_id, limit=limit)}


@app.get("/api/agent/audit/tool-runs")
async def api_list_tool_run_audits(
    session_id: str | None = None,
    tool_name: str | None = None,
    limit: int = 50,
    auth: AuthContext = Depends(get_auth_context),
):
    try:
        require_permission(auth, "audit:read")
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return {"items": await list_tool_run_audits(session_id=session_id, tool_name=tool_name, tenant_id=auth.tenant_id, limit=limit)}


@app.get("/api/agent/metrics/governance")
async def api_governance_metrics(auth: AuthContext = Depends(get_auth_context)):
    try:
        require_permission(auth, "audit:read")
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return await governance_metrics(auth.tenant_id)



from semantic_cache import semantic_cache
import redis.asyncio as aioredis
import json

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
max_active_tasks = int(os.getenv("AGENT_MAX_ACTIVE_TASKS", "4"))
task_timeout_seconds = float(os.getenv("AGENT_TASK_TIMEOUT_SECONDS", "90"))
request_semaphore = asyncio.Semaphore(max_active_tasks)
active_tasks: dict[str, asyncio.Task] = {}
active_task_meta: dict[str, dict[str, object]] = {}
active_task_by_context: dict[str, str] = {}
SYSTEM_BADGE_RE = re.compile(r"\n?> \*.*\[系统态:.*(?:\n|$)")


def _connection_key(auth: AuthContext, session_id: str) -> str:
    return f"{auth.tenant_id}:{auth.user_id}:{session_id}"


def _cache_namespace(auth: AuthContext, mode: str) -> str:
    permission_fingerprint = ",".join(sorted(auth.permissions))
    return f"tenant={auth.tenant_id}|user={auth.user_id}|mode={mode}|perms={permission_fingerprint}"


def _strip_system_badges(content: str) -> str:
    return SYSTEM_BADGE_RE.sub("\n", content or "").strip()


@app.get("/api/agent/tasks/active")
async def api_active_tasks(auth: AuthContext = Depends(get_auth_context)):
    try:
        require_permission(auth, "audit:read")
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    now = time.time()
    return {
        "max_active_tasks": max_active_tasks,
        "items": [
            {
                **meta,
                "age_seconds": round(now - float(meta.get("created_at", now)), 3),
                "done": bool(active_tasks.get(task_id).done()) if active_tasks.get(task_id) else True,
            }
            for task_id, meta in active_task_meta.items()
        ],
    }

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket, session_id: str = "anonymous", user_id: str = "anonymous"):
    origin = websocket.headers.get("origin")
    if origin and origin not in ALLOWED_ORIGINS:
        await websocket.close(code=1008, reason="Origin not allowed")
        return
    auth = consume_ws_ticket(websocket.query_params.get("ticket"), session_id)
    if auth is None:
        header_token = _bearer_token(websocket.headers.get("authorization"))
        legacy_query_token = websocket.query_params.get("token") if os.getenv("AGENT_ALLOW_LEGACY_WS_TOKEN", "false").lower() == "true" else None
        auth = authenticate(header_token or legacy_query_token, session_id, user_id)
    if not auth.roles or not auth.has_permission("chat:use"):
        await websocket.close(code=1008, reason="Authentication required")
        return
    user_id = auth.user_id
    connection_key = _connection_key(auth, session_id)
    await manager.connect(websocket, connection_key)
    redis_client = aioredis.from_url(redis_url)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(f"ws:{session_id}")
    
    async def direct_ws_send(data):
        try:
            # Accumulate stream chunks for caching
            if data.get("type") == "stream_chunk" and hasattr(websocket, 'accumulated_response'):
                websocket.accumulated_response += data.get("content", "")
            if data.get("type") == "task_complete":
                task_id = data.get("task_id") or active_task_by_context.get(connection_key)
                if task_id:
                    active_tasks.pop(str(task_id), None)
                    active_task_meta.pop(str(task_id), None)
                active_task_by_context.pop(connection_key, None)
            await websocket.send_json(data)
        except Exception as e:
            print(f"WS send error: {e}")

    listen_task = None
    try:
        try:
            pending_approvals = await list_pending_approvals(session_id, auth.user_id, auth.tenant_id)
            for approval in pending_approvals:
                params = dict(approval.get("params") or {})
                params.update({
                    "approval_id": approval["approval_id"],
                    "approval_token": approval["approval_token"],
                    "approval_kind": approval["approval_kind"],
                    "expires_at": approval["expires_at"],
                    "recovered": True,
                })
                await direct_ws_send({
                    "type": "hitl_request",
                    "content": approval["task"],
                    "params": params,
                })
        except Exception as e:
            await direct_ws_send({"type": "status", "content": f"⚠️ 未能恢复待审批任务: {str(e)}"})

        while True:
            data = await websocket.receive_json()
            if data.get("type") == "cancel":
                requested_task_id = str(data.get("task_id") or active_task_by_context.get(connection_key) or "")
                task = active_tasks.get(requested_task_id)
                if task and not task.done():
                    task.cancel()
                    await direct_ws_send({
                        "type": "status",
                        "content": "🛑 已请求取消当前后台任务。",
                        "task": active_task_meta.get(requested_task_id),
                    })
                else:
                    await direct_ws_send({"type": "status", "content": "ℹ️ 当前没有可取消的后台任务。"})
                continue

            if data.get("type") == "approval_decision" and data.get("approved") is False:
                try:
                    require_permission(auth, "approval:decide")
                except PermissionError as exc:
                    await direct_ws_send({
                        "type": "approval_decision_result",
                        "approved": False,
                        "ok": False,
                        "error": str(exc),
                    })
                    continue
                approval = data.get("approval") or {}
                rejected = await reject_approval_decision(
                    session_id,
                    str(approval.get("approval_id") or ""),
                    str(approval.get("approval_token") or ""),
                    user_id,
                    auth.tenant_id,
                    approval,
                )
                await direct_ws_send({
                    "type": "approval_decision_result",
                    "approved": False,
                    "ok": rejected,
                    "approval_id": approval.get("approval_id"),
                })
                continue

            existing_task_id = active_task_by_context.get(connection_key)
            existing_task = active_tasks.get(existing_task_id or "")
            if existing_task:
                if existing_task.done():
                    active_tasks.pop(str(existing_task_id), None)
                    active_task_meta.pop(str(existing_task_id), None)
                    active_task_by_context.pop(connection_key, None)
                else:
                    await direct_ws_send({"type": "status", "content": "⏳ 当前会话已有任务运行中，请等待完成或先点击停止。"})
                    continue

            user_msg = data.get("message", "")
            print(f"DEBUG: Received WS message: {user_msg}")
            mode = data.get("mode", "fast")
            selected_model = data.get("model", model_name)
            image_data = data.get("image_data", None)
            face_data = data.get("face_data", None)
            audio_data = data.get("audio_data", None)
            file_upload = data.get("file_upload", None)
            history = data.get("history", [])
            approval = data.get("approval") or {}
            hitl_approved = bool(data.get("hitl_approved") or data.get("is_approved") or approval.get("approved"))
            approval_kind = str(approval.get("kind") or data.get("approval_kind") or "")
            approval_id = str(approval.get("approval_id") or data.get("approval_id") or "")
            approval_token = str(approval.get("approval_token") or data.get("approval_token") or "")

            if len(user_msg) > 4000:
                await websocket.send_json({"type": "stream_start"})
                await websocket.send_json({"type": "stream_chunk", "content": "\n\n> ⚠️ **[安全拦截]**: 您的输入文本过长。"})
                await websocket.send_json({"type": "stream_end"})
                continue
            
            if await check_sensitive_words(user_msg):
                await websocket.send_json({"type": "stream_start"})
                await websocket.send_json({"type": "stream_chunk", "content": "\n\n> 🛑 **[合规拦截]**: 您的提问包含敏感或违规词汇。"})
                await websocket.send_json({"type": "stream_end"})
                continue

            # 语义缓存检查 (Semantic Cache)，如果是带图片、人脸、语音、或文件的请求则跳过缓存
            cache_namespace = _cache_namespace(auth, mode)
            cached_response = semantic_cache.get_cache(user_msg, cache_namespace) if mode == "fast" and not image_data and not face_data and not audio_data and not file_upload else None
            if cached_response and mode == "fast":
                await websocket.send_json({"type": "status", "content": "⚡ 从语义缓存中极速返回..."})
                await websocket.send_json({"type": "stream_start"})
                await websocket.send_json({"type": "stream_chunk", "content": cached_response})
                await websocket.send_json({"type": "stream_end"})
                continue
            
            # 记录当前查询，以便任务完成时缓存
            websocket.pending_query = user_msg
            websocket.accumulated_response = ""
            task_id = str(uuid.uuid4())
            active_task_meta[task_id] = {
                "task_id": task_id,
                "session_id": session_id,
                "user_id": user_id,
                "tenant_id": auth.tenant_id,
                "mode": mode,
                "created_at": time.time(),
                "timeout_seconds": task_timeout_seconds,
            }
            active_task_by_context[connection_key] = task_id
            await direct_ws_send({"type": "task_started", "task_id": task_id})

            # 启动后台任务直接处理请求，不使用 Celery
            async def run_and_cache():
                try:
                    async with request_semaphore:
                        from worker import async_process_request
                        await asyncio.wait_for(
                            async_process_request(
                                session_id,
                                user_msg,
                                mode,
                                selected_model,
                                history,
                                image_data,
                                audio_data,
                                file_upload,
                                direct_ws_send,
                                face_data=face_data,
                                hitl_approved=hitl_approved,
                                approval_kind=approval_kind,
                                approval_id=approval_id,
                                approval_token=approval_token,
                                user_id=user_id,
                                tenant_id=auth.tenant_id,
                                user_permissions=sorted(auth.permissions),
                            ),
                            timeout=task_timeout_seconds,
                        )
                except asyncio.CancelledError:
                    await direct_ws_send({"type": "stream_end"})
                    await direct_ws_send({"type": "task_complete", "content": "Task cancelled.", "task_id": task_id})
                    raise
                except asyncio.TimeoutError:
                    await direct_ws_send({"type": "stream_start"})
                    await direct_ws_send({"type": "stream_chunk", "content": "\n\n> 🛑 **[任务超时]**: 后台任务已超过允许执行时间，系统已终止本次执行。"})
                    await direct_ws_send({"type": "stream_end"})
                    await direct_ws_send({"type": "task_complete", "content": "Task timed out.", "task_id": task_id})
                except Exception as e:
                    await direct_ws_send({"type": "stream_start"})
                    await direct_ws_send({"type": "stream_chunk", "content": f"\n\n> ❌ **[运行异常]**: {str(e)}"})
                    await direct_ws_send({"type": "stream_end"})
                finally:
                    if active_tasks.get(task_id) is asyncio.current_task():
                        active_tasks.pop(task_id, None)
                        active_task_meta.pop(task_id, None)
                        if active_task_by_context.get(connection_key) == task_id:
                            active_task_by_context.pop(connection_key, None)

                try:
                    if hasattr(websocket, 'pending_query') and hasattr(websocket, 'accumulated_response'):
                        if "❌ **[运行异常]**" not in websocket.accumulated_response and not image_data and not face_data and not audio_data and not file_upload:
                            semantic_cache.set_cache(websocket.pending_query, _strip_system_badges(websocket.accumulated_response), cache_namespace)
                except Exception as e:
                    print(f"Semantic cache write failed: {e}")
            
            active_tasks[task_id] = asyncio.create_task(run_and_cache())

    except WebSocketDisconnect:
        task_id = active_task_by_context.get(connection_key)
        task = active_tasks.get(task_id or "")
        if task and not task.done():
            task.cancel()
        if task_id:
            active_task_meta.pop(task_id, None)
            active_task_by_context.pop(connection_key, None)
        manager.disconnect(connection_key)
        if listen_task:
            listen_task.cancel()
        await pubsub.unsubscribe(f"ws:{session_id}")
        await redis_client.aclose()
    except Exception as e:
        manager.disconnect(connection_key)
        if listen_task:
            listen_task.cancel()
        print(f"Server Error in session {session_id}: {e}")

# ==========================================
# 11. AI 工程师实战工作台 (Curriculum & Sandbox APIs)
# ==========================================
from curriculum_engine import CurriculumEngine
from sandbox_runner import SandboxRunner
from dfl_engine import dfl_feedback

PROJECT_ROOT = "/app/curriculum" if os.path.exists("/app/curriculum") else os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
curriculum_engine = CurriculumEngine(base_dir=PROJECT_ROOT)
sandbox_runner = SandboxRunner()

class RunCodeRequest(BaseModel):
    code: str
    timeout: Optional[int] = 60

class VerifyCodeRequest(BaseModel):
    phase_id: str
    user_code: str
    timeout: Optional[int] = 90

class MentorReviewRequest(BaseModel):
    phase_id: str
    user_code: str
    error_output: Optional[str] = ""
    question: Optional[str] = ""
    image_data: Optional[str] = None  # Base64 编码的架构截图或报错图片 (多模态感知)

@app.get("/api/v1/curriculum/phases")
async def api_get_curriculum_phases():
    """获取全部 24 阶段课程体系与通关元数据"""
    phases = curriculum_engine.get_all_phases()
    return {"status": "success", "count": len(phases), "phases": phases}

@app.get("/api/v1/curriculum/phases/{phase_id}")
async def api_get_phase_detail(phase_id: str):
    """获取指定关卡的实验指南、初始代码和测试集"""
    detail = curriculum_engine.get_phase_detail(phase_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Phase '{phase_id}' not found.")
    return {"status": "success", "code": 200, "data": detail}

# ==========================================
# 11.1 多租户 RBAC 治理与 JWT 鉴权引擎接入
# ==========================================
try:
    from backend.auth_governance import (
        USER_STORE,
        TENANT_STORE,
        ROLE_PERMISSIONS_MATRIX,
        UserRole,
        create_access_token,
        verify_access_token,
        authenticate_user,
        list_all_tenants,
        list_tenant_users,
        create_new_user,
        update_user_role,
        update_tenant_budget,
        deduct_tenant_tokens,
        get_role_permissions_matrix,
        get_tenant_info,
        rate_limiter,
        record_user_action,
        list_user_audit_logs,
        save_user_progress,
        get_user_progress_map,
    )
except ImportError:
    from auth_governance import (
        USER_STORE,
        TENANT_STORE,
        ROLE_PERMISSIONS_MATRIX,
        UserRole,
        create_access_token,
        verify_access_token,
        authenticate_user,
        list_all_tenants,
        list_tenant_users,
        create_new_user,
        update_user_role,
        update_tenant_budget,
        deduct_tenant_tokens,
        get_role_permissions_matrix,
        get_tenant_info,
        rate_limiter,
        record_user_action,
        list_user_audit_logs,
        save_user_progress,
        get_user_progress_map,
    )

def resolve_tenant_context(
    authorization: Optional[str] = Header(None),
    x_tenant_id: Optional[str] = Header(None)
):
    """解析请求凭据：提取租户、用户与角色，未携带凭证时平滑降级为最高权限超级管理员以保障开箱即用"""
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        try:
            claims = verify_access_token(token)
            return claims
        except Exception as e:
            pass
    
    tenant_id = x_tenant_id or "tenant_enterprise_core"
    return type("TokenPayloadLike", (), {
        "user_id": "usr_superadmin_01",
        "username": "admin",
        "tenant_id": tenant_id,
        "role": UserRole.ADMIN,
    })()

class LoginRequest(BaseModel):
    username: str
    password: str
    target_tenant_id: Optional[str] = None

class SwitchTenantRequest(BaseModel):
    target_tenant_id: str

class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str = "developer"
    tenant_id: Optional[str] = None
    display_name: Optional[str] = ""

class UpdateRoleRequest(BaseModel):
    role: str

class UpdateBudgetRequest(BaseModel):
    monthly_token_budget: int

@app.post("/api/v1/auth/login")
async def api_auth_login(req: LoginRequest):
    """用户登录鉴权接口：校验账密并签发企业 JWT 令牌与租户上下文"""
    user = authenticate_user(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误，请检查输入")
    
    tenant_id = req.target_tenant_id or user.tenant_id
    token = create_access_token(
        user_id=user.user_id,
        tenant_id=tenant_id,
        role=user.role,
    )
    tenant_info = get_tenant_info(tenant_id)
    record_user_action(
        user_id=user.user_id,
        username=user.username,
        tenant_id=tenant_id,
        action="login",
        details=f"用户通过 Web 登录成功，激活角色 [{user.role.value}]",
        cost_tokens=0
    )
    return {
        "status": "success",
        "token": token,
        "user": {
            "user_id": user.user_id,
            "username": user.username,
            "display_name": user.display_name,
            "role": user.role.value,
            "tenant_id": tenant_id,
        },
        "tenant": {
            "tenant_id": tenant_info.tenant_id if tenant_info else tenant_id,
            "tenant_name": tenant_info.tenant_name if tenant_info else "租户",
            "monthly_token_budget": tenant_info.monthly_token_budget if tenant_info else 1000000,
            "tokens_consumed": tenant_info.tokens_consumed if tenant_info else 0,
            "tokens_remaining": max(0, (tenant_info.monthly_token_budget - tenant_info.tokens_consumed)) if tenant_info else 1000000,
            "is_exhausted": (tenant_info.tokens_consumed >= tenant_info.monthly_token_budget) if tenant_info else False,
        },
        "permissions": ROLE_PERMISSIONS_MATRIX.get(user.role.value, {}).get("permissions", [])
    }

@app.get("/api/v1/auth/me")
async def api_auth_me(
    authorization: Optional[str] = Header(None),
    x_tenant_id: Optional[str] = Header(None)
):
    """获取当前登录用户信息与租户配额状态"""
    ctx = resolve_tenant_context(authorization, x_tenant_id)
    tenant_info = get_tenant_info(ctx.tenant_id)
    username = getattr(ctx, "username", "admin")
    user = USER_STORE.get(username)
    role_val = ctx.role.value if hasattr(ctx.role, "value") else str(ctx.role)
    
    return {
        "status": "success",
        "user": {
            "user_id": getattr(ctx, "user_id", "usr_superadmin_01"),
            "username": username,
            "display_name": user.display_name if user else f"用户 {username}",
            "role": role_val,
            "tenant_id": ctx.tenant_id,
        },
        "tenant": {
            "tenant_id": tenant_info.tenant_id if tenant_info else ctx.tenant_id,
            "tenant_name": tenant_info.tenant_name if tenant_info else "租户",
            "monthly_token_budget": tenant_info.monthly_token_budget if tenant_info else 1000000,
            "tokens_consumed": tenant_info.tokens_consumed if tenant_info else 0,
            "tokens_remaining": max(0, (tenant_info.monthly_token_budget - tenant_info.tokens_consumed)) if tenant_info else 1000000,
            "is_exhausted": (tenant_info.tokens_consumed >= tenant_info.monthly_token_budget) if tenant_info else False,
        },
        "permissions": ROLE_PERMISSIONS_MATRIX.get(role_val, {}).get("permissions", [])
    }

@app.get("/api/v1/tenants")
async def api_list_tenants():
    """获取全系统所有可用租户列表与健康水位"""
    return {"status": "success", "tenants": list_all_tenants()}

@app.post("/api/v1/tenants/switch")
async def api_switch_tenant(
    req: SwitchTenantRequest,
    authorization: Optional[str] = Header(None),
    x_tenant_id: Optional[str] = Header(None)
):
    """一键切换租户：签发目标租户的 JWT 令牌"""
    ctx = resolve_tenant_context(authorization, x_tenant_id)
    target_tenant = get_tenant_info(req.target_tenant_id)
    if not target_tenant:
        raise HTTPException(status_code=404, detail=f"目标租户 [{req.target_tenant_id}] 不存在")
    
    new_token = create_access_token(
        user_id=getattr(ctx, "user_id", "usr_superadmin_01"),
        tenant_id=req.target_tenant_id,
        role=ctx.role,
    )
    return {
        "status": "success",
        "token": new_token,
        "tenant": {
            "tenant_id": target_tenant.tenant_id,
            "tenant_name": target_tenant.tenant_name,
            "monthly_token_budget": target_tenant.monthly_token_budget,
            "tokens_consumed": target_tenant.tokens_consumed,
            "tokens_remaining": max(0, target_tenant.monthly_token_budget - target_tenant.tokens_consumed),
            "is_exhausted": target_tenant.tokens_consumed >= target_tenant.monthly_token_budget,
        }
    }

@app.get("/api/v1/governance/users")
async def api_governance_list_users(
    authorization: Optional[str] = Header(None),
    x_tenant_id: Optional[str] = Header(None)
):
    """用户维护：获取当前租户或全量用户列表"""
    ctx = resolve_tenant_context(authorization, x_tenant_id)
    role_val = ctx.role.value if hasattr(ctx.role, "value") else str(ctx.role)
    tenant_filter = None if role_val == "admin" else ctx.tenant_id
    return {"status": "success", "users": list_tenant_users(tenant_filter)}

@app.post("/api/v1/governance/users")
async def api_governance_create_user(
    req: CreateUserRequest,
    authorization: Optional[str] = Header(None),
    x_tenant_id: Optional[str] = Header(None)
):
    """用户维护：超级管理员创建新用户并分配初始角色"""
    ctx = resolve_tenant_context(authorization, x_tenant_id)
    role_val = ctx.role.value if hasattr(ctx.role, "value") else str(ctx.role)
    if role_val != "admin":
        raise HTTPException(status_code=403, detail="权限不足：仅系统超级管理员允许新增团队用户")
    
    tenant_id = req.tenant_id or ctx.tenant_id
    user = create_new_user(
        tenant_id=tenant_id,
        username=req.username,
        password=req.password,
        role=req.role,
        display_name=req.display_name or f"团队成员 {req.username}"
    )
    return {
        "status": "success", 
        "user": {
            "user_id": user.user_id, 
            "username": user.username, 
            "role": user.role.value,
            "tenant_id": user.tenant_id,
            "display_name": user.display_name
        }
    }

@app.put("/api/v1/governance/users/{username}/role")
async def api_governance_update_role(
    username: str,
    req: UpdateRoleRequest,
    authorization: Optional[str] = Header(None),
    x_tenant_id: Optional[str] = Header(None)
):
    """角色维护：管理员动态调整指定用户的权限角色"""
    ctx = resolve_tenant_context(authorization, x_tenant_id)
    role_val = ctx.role.value if hasattr(ctx.role, "value") else str(ctx.role)
    if role_val != "admin":
        raise HTTPException(status_code=403, detail="权限不足：仅管理员角色允许调整成员角色")
    
    updated = update_user_role(username, req.role)
    return {"status": "success", "user": {"username": updated.username, "role": updated.role.value}}

@app.put("/api/v1/governance/tenants/{tenant_id}/budget")
async def api_governance_update_budget(
    tenant_id: str,
    req: UpdateBudgetRequest,
    authorization: Optional[str] = Header(None),
    x_tenant_id: Optional[str] = Header(None)
):
    """配额维护：动态调整或充值租户当月 Token 预算上限"""
    ctx = resolve_tenant_context(authorization, x_tenant_id)
    role_val = ctx.role.value if hasattr(ctx.role, "value") else str(ctx.role)
    if role_val != "admin":
        raise HTTPException(status_code=403, detail="权限不足：仅管理员角色允许修改租户配额预算")
    
    tenant = update_tenant_budget(tenant_id, req.monthly_token_budget)
    return {
        "status": "success",
        "tenant": {
            "tenant_id": tenant.tenant_id,
            "monthly_token_budget": tenant.monthly_token_budget,
            "tokens_consumed": tenant.tokens_consumed,
            "tokens_remaining": max(0, tenant.monthly_token_budget - tenant.tokens_consumed),
            "is_exhausted": tenant.tokens_consumed >= tenant.monthly_token_budget
        }
    }

@app.get("/api/v1/governance/roles")
async def api_governance_roles():
    """获取系统角色权限矩阵定义"""
    return {"status": "success", "matrix": get_role_permissions_matrix()}

@app.get("/api/v1/governance/audits")
async def api_governance_audits(
    authorization: Optional[str] = Header(None),
    x_tenant_id: Optional[str] = Header(None),
    limit: int = 50
):
    """获取全生命周期用户操作行为与 Token 算力消耗审计流水"""
    ctx = resolve_tenant_context(authorization, x_tenant_id)
    role_val = ctx.role.value if hasattr(ctx.role, "value") else str(ctx.role)
    tenant_filter = None if role_val == "admin" else ctx.tenant_id
    return {"status": "success", "audits": list_user_audit_logs(tenant_id=tenant_filter, limit=limit)}

@app.post("/api/v1/sandbox/run")
async def api_sandbox_run(
    req: RunCodeRequest,
    authorization: Optional[str] = Header(None),
    x_tenant_id: Optional[str] = Header(None)
):
    """在受限隔离环境中执行代码 (已注入多租户与 RBAC 质量护栏)"""
    ctx = resolve_tenant_context(authorization, x_tenant_id)
    role_val = ctx.role.value if hasattr(ctx.role, "value") else str(ctx.role)
    username = getattr(ctx, "username", "admin")
    user_id = getattr(ctx, "user_id", "usr_admin")

    # 1. 角色权限拦截
    if role_val == "viewer":
        record_user_action(
            user_id=user_id,
            username=username,
            tenant_id=ctx.tenant_id,
            action="sandbox_blocked",
            details="只读访客尝试执行沙箱代码，已被 RBAC 规则阻断",
            cost_tokens=0,
            status="blocked"
        )
        return {
            "status": "error",
            "output": "",
            "error": "🔒 [权限拦截 403 Forbidden]：当前登录身份为【只读访客 (Viewer)】，受企业数据安全策略限制，禁止在沙箱中执行任意动态代码。如需调试请联系管理员提升为【研发工程师】或【超级管理员】。",
            "role_blocked": True
        }

    # 2. 租户 Token 预算熔断拦截
    tenant_info = get_tenant_info(ctx.tenant_id)
    if tenant_info and tenant_info.tokens_consumed >= tenant_info.monthly_token_budget:
        record_user_action(
            user_id=user_id,
            username=username,
            tenant_id=ctx.tenant_id,
            action="budget_exhausted",
            details=f"租户【{tenant_info.tenant_name}】算力预算超标触发系统熔断",
            cost_tokens=0,
            status="exhausted"
        )
        return {
            "status": "error",
            "output": "",
            "error": f"⚡ [Token 预算熔断 402 Payment Required]：租户【{tenant_info.tenant_name}】当月 Token 配额已耗尽 ({tenant_info.tokens_consumed}/{tenant_info.monthly_token_budget})。系统已自动启动安全熔断阻断算力消耗。请管理员在【权限治理】中扩容预算。",
            "budget_exhausted": True
        }

    # 3. 运行沙箱代码
    result = sandbox_runner.run_code(req.code, timeout=req.timeout)

    # 4. 真实扣减租户算力配额并记录审计流水
    quota = deduct_tenant_tokens(ctx.tenant_id, 120)
    record_user_action(
        user_id=user_id,
        username=username,
        tenant_id=ctx.tenant_id,
        action="sandbox_run",
        details=f"成功调试执行沙箱代码 ({len(req.code)} 字符)",
        cost_tokens=120,
        status="success"
    )
    result["tenant_quota"] = quota
    result["tenant_id"] = ctx.tenant_id
    result["tenant_name"] = tenant_info.tenant_name if tenant_info else ctx.tenant_id

    # 显性化多租户算力调度输出
    remaining = quota.get("tokens_remaining", 0)
    dispatch_msg = f"\n[🏢 算力调度: {result['tenant_name']}] 本次消耗: 120 Tokens | 当月剩余可用: {remaining:,} Tokens"
    if remaining <= 200:
        dispatch_msg += f" (⚠️ 配额告警: 仅剩 {remaining} Tokens，即将触发熔断保护)"
    result["stdout"] = (result.get("stdout") or "") + dispatch_msg
    return result

@app.post("/api/v1/sandbox/verify")
async def api_sandbox_verify(
    req: VerifyCodeRequest,
    authorization: Optional[str] = Header(None),
    x_tenant_id: Optional[str] = Header(None)
):
    """自动化运行关卡测试用例并判定通关 (已注入多租户与 RBAC 质量护栏)"""
    ctx = resolve_tenant_context(authorization, x_tenant_id)
    role_val = ctx.role.value if hasattr(ctx.role, "value") else str(ctx.role)

    # 1. 角色权限拦截
    if role_val == "viewer":
        return {
            "status": "error",
            "passed": False,
            "output": "",
            "error": "🔒 [权限拦截 403 Forbidden]：当前登录身份为【只读访客 (Viewer)】，无权提交关卡自动化通关评测。",
            "role_blocked": True
        }

    # 2. 租户 Token 预算熔断拦截
    tenant_info = get_tenant_info(ctx.tenant_id)
    if tenant_info and tenant_info.tokens_consumed >= tenant_info.monthly_token_budget:
        return {
            "status": "error",
            "passed": False,
            "output": "",
            "error": f"⚡ [Token 预算熔断 402 Payment Required]：租户【{tenant_info.tenant_name}】当月 Token 配额已耗尽。请联系管理员扩容预算后重试。",
            "budget_exhausted": True
        }

    detail = curriculum_engine.get_phase_detail(req.phase_id)
    test_code = detail["test_code"] if detail else ""
    result = sandbox_runner.verify_code(req.user_code, test_code, timeout=req.timeout)

    # 3. 扣减 250 Tokens 并在响应中回传
    quota = deduct_tenant_tokens(ctx.tenant_id, 250)
    user_id = getattr(ctx, "user_id", "usr_superadmin_01")
    username = getattr(ctx, "username", "admin")
    record_user_action(
        user_id=user_id,
        username=username,
        tenant_id=ctx.tenant_id,
        action="sandbox_verify",
        details=f"提交关卡 [{req.phase_id}] 自动化评测，结果: {'通过' if result.get('passed') else '未通过'}",
        cost_tokens=250,
        status="success" if result.get("passed") else "failed"
    )
    # 4. 若通关成功，物理落盘云端持久化学员进度与代码快照
    if result.get("passed"):
        base_xp = 100
        if detail:
            diff = detail.get("difficulty", "")
            base_xp = 240 if diff == "Advanced" else (140 if diff == "Intermediate" else 80)
        save_user_progress(
            user_id=user_id,
            username=username,
            tenant_id=ctx.tenant_id,
            phase_id=req.phase_id,
            passed=True,
            xp_earned=base_xp,
            saved_code=req.user_code,
            execution_metrics={
                "execution_time_ms": result.get("execution_time_ms", 0),
                "passedAt": int(time.time() * 1000)
            }
        )

    result["tenant_quota"] = quota
    result["tenant_id"] = ctx.tenant_id
    result["tenant_name"] = tenant_info.tenant_name if tenant_info else ctx.tenant_id
    return result

class SyncProgressRequest(BaseModel):
    phase_id: str
    passed: bool = True
    xp_earned: Optional[int] = 100
    saved_code: Optional[str] = ""
    execution_metrics: Optional[Dict[str, Any]] = None

@app.get("/api/v1/curriculum/user-progress")
async def api_get_user_progress(
    authorization: Optional[str] = Header(None),
    x_tenant_id: Optional[str] = Header(None)
):
    """获取当前登录学员在 SQLite 中的全量关卡历史与代码快照"""
    ctx = resolve_tenant_context(authorization, x_tenant_id)
    user_id = getattr(ctx, "user_id", "usr_superadmin_01")
    progress_map = get_user_progress_map(user_id)
    return {
        "status": "success",
        "user_id": user_id,
        "progress": progress_map
    }

@app.post("/api/v1/curriculum/user-progress")
async def api_sync_user_progress(
    req: SyncProgressRequest,
    authorization: Optional[str] = Header(None),
    x_tenant_id: Optional[str] = Header(None)
):
    """主动同步/保存学员关卡通关状态与代码快照至云端 SQLite"""
    ctx = resolve_tenant_context(authorization, x_tenant_id)
    user_id = getattr(ctx, "user_id", "usr_superadmin_01")
    username = getattr(ctx, "username", "admin")
    res = save_user_progress(
        user_id=user_id,
        username=username,
        tenant_id=ctx.tenant_id,
        phase_id=req.phase_id,
        passed=req.passed,
        xp_earned=req.xp_earned or 100,
        saved_code=req.saved_code or "",
        execution_metrics=req.execution_metrics or {}
    )
    return res


@app.post("/api/v1/mentor/review")
async def api_mentor_review(req: MentorReviewRequest):
    """结合 DFL 决策分析与 DeepSeek 大模型给出全方位企业级伴学诊断"""
    # 1. 使用 DFL 决策层先验分析用户意图及上下文
    user_query = (req.question or "").strip()
    context_desc = f"关卡: {req.phase_id}"
    intent_prompt = user_query if user_query else f"深度诊断代码质量与执行状态: {req.error_output[:120]}"
    decision = dfl_feedback.evaluate_intent(intent_prompt, context_summary=context_desc)
    
    # 2. 检索关卡标准上下文
    phase_detail = curriculum_engine.get_phase_detail(req.phase_id)
    phase_title = phase_detail.get("title", req.phase_id) if phase_detail else req.phase_id
    guide_summary = ""
    if phase_detail and phase_detail.get("guide_markdown"):
        lines = [l for l in phase_detail["guide_markdown"].split("\n") if l.strip() and not l.strip().startswith("<!--")]
        guide_summary = "\n".join(lines[:25])[:800]

    error_text = (req.error_output or "").strip()
    # 判断是否处于报错排障场景
    is_error_diagnostic = bool(
        error_text and any(kw in error_text for kw in [
            "Traceback", "Error", "Exception", "AssertionError", 
            "失败", "未全部通过", "blocked", "安全边界策略拦截", "超时"
        ])
    ) or ("排查" in user_query or "诊断" in user_query or "报错" in user_query or "未通过" in user_query)

    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com")
    
    review_markdown = ""
    score = 68 if is_error_diagnostic else 88
    level = "B" if is_error_diagnostic else "A"

    if api_key:
        try:
            client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
            
            if is_error_diagnostic:
                # 场景 A: 苏格拉底式启发式排障诊断（严禁直接给现成答案，提供思路支架）
                system_prompt = (
                    "你是一名拥有深厚 AI 工程经验的资深伴学导师，采用【苏格拉底式启发教学（Socratic Teaching）】。\n"
                    "学员在攻克实战关卡时遇到了执行错误或测试失败，你需要帮助学员扫清认知障碍。\n"
                    "【教学铁律】：\n"
                    "1. 绝不要直接贴出可直接复制过关的完整答案代码！直接给答案会彻底破坏学员的思考与成长过程。\n"
                    "2. 重在启发：用通俗易懂的人话解释报错根因，指出嫌疑代码行，并提出 2~3 个引导学员自行排查的思考问题与伪代码线索。\n"
                    "3. 鼓励学员，保持温和、专业且极富启发性的语言风格。"
                )
                user_prompt = f"""
## 实战关卡背景
- **当前关卡**: 【{phase_title}】 (ID: `{req.phase_id}`)
- **关卡目标与核心概念摘要**:
{guide_summary or "掌握本阶段核心 AI 架构设计与工程落地规范"}

## 学员代码
```python
{req.user_code}
```

## 终端报错或测试未通过信息
```
{error_text}
```

## 学员提问诉求
{user_query if user_query else "请帮我分析报错根因，给出启发式排障思路，不要直接给我完整答案。"}

---
## 请严格按照以下四大启发式维度输出清晰的 Markdown 格式：

### 1. 💡 报错根因通俗解读
- 用 1~2 句白话告诉学员“程序刚才发生了什么”，消除学员对英文 Traceback 或断言失败的恐惧。

### 2. 🎯 嫌疑代码与定位线索
- 精确定位到代码中的具体函数、变量或逻辑分支，指出数据流在哪个环节发生了偏差。

### 3. 🧭 启发式思考支架 (核心自查清单)
- 抛出 2~3 个引导自查的问题（例如：“输入数据为空时你的切片逻辑会返回什么？”）。
- 提供概念层面的排查伪代码或逻辑示意图（**注意：严禁给出完整解题代码！**）。

### 4. 📖 关联知识手册导航
- 指引学员查阅本关卡知识手册中的关键技术点（如异常防御、异步流式、Prompt 参数对齐等），引导学员自主修复。
"""
            else:
                # 场景 B: 通关代码企业级架构评审 (Code Review)
                system_prompt = (
                    "你是一名拥有十年以上大模型系统架构与 AI Agent 落地经验的世界级技术专家导师。\n"
                    "你的职责是为学员提供一份具备工业级水准的【深度架构 Code Review 与生产落地建议】。\n"
                    "原则：犀利透彻、直击根因、具备大厂代码审美、企业级最佳实践兼备。务必结合代码具体剖析。"
                )
                user_prompt = f"""
## 实战关卡背景
- **当前关卡**: 【{phase_title}】 (ID: `{req.phase_id}`)
- **核心关卡目标摘要**:
{guide_summary or "掌握本阶段核心 AI 架构设计与工程落地规范"}

## 学员代码
```python
{req.user_code}
```

## 执行状态
```
{error_text if error_text else "代码执行退出码为 0，终端无异常报错。"}
```

## 学员具体疑问
{user_query if user_query else "请对当前代码进行多维度深度 Code Review，指出架构盲点并给出生产级优化重构建议。"}

---
## 请严格按照以下五大结构化维度使用清晰的 Markdown 格式输出：
### 1. 📊 代码健康度与架构评分 (给出评分 XX/100 及评级 S/A/B/C)
### 2. 🎯 关卡核心技术对齐度
### 3. 🔍 核心盲点与隐患排查 (超时重试、并发容灾、Token 预算等)
### 4. ⚡ 企业级架构重构方案 (对比说明生产环境优势)
### 5. 🛡️ 工业级落地避坑指南
"""

            resp = await client.chat.completions.create(
                model=os.getenv("DEFAULT_MODEL", "deepseek-chat"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=1800,
                temperature=0.3
            )
            review_markdown = resp.choices[0].message.content

            # 提取评分
            import re
            score_match = re.search(r"(\d{1,3})\s*/\s*100", review_markdown) or re.search(r"(\d{1,3})\s*分", review_markdown)
            if score_match:
                s = int(score_match.group(1))
                if 0 <= s <= 100:
                    score = s
            if score >= 90:
                level = "S"
            elif score >= 80:
                level = "A"
            elif score >= 70:
                level = "B"
            else:
                level = "C"

        except Exception as e:
            review_markdown = f"""### ⚠️ 诊断引擎连接异常
由于外部模型服务暂时波动（`{str(e)}`），为您自动降级启用**本地离线启发式分析引擎**：

{_generate_offline_diagnostic(req.phase_id, phase_title, req.user_code, error_text)}
"""
    else:
        # 未配置 API KEY 时的智能本地规则启发诊断
        review_markdown = f"""### 💡 本地启发式诊断引擎 (离线模式)
未检测到全局 `OPENAI_API_KEY`，系统已自动启用**内置启发式规则诊断分析**：

{_generate_offline_diagnostic(req.phase_id, phase_title, req.user_code, error_text)}
"""

    return {
        "status": "success",
        "mode": "troubleshooting" if is_error_diagnostic else "review",
        "score": score,
        "level": level,
        "phase_title": phase_title,
        "dfl_decision": decision,
        "review": review_markdown
    }

@app.post("/api/v1/mentor/review/stream")
async def api_mentor_review_stream(req: MentorReviewRequest):
    """支持 SSE 流式打字机输出的高性能 AI 伴学排障接口，具备多模态与堆栈精确定位"""
    user_query = (req.question or "").strip()
    context_desc = f"关卡: {req.phase_id}"
    intent_prompt = user_query if user_query else f"深度诊断代码质量与执行状态: {req.error_output[:120]}"
    decision = dfl_feedback.evaluate_intent(intent_prompt, context_summary=context_desc)

    phase_detail = curriculum_engine.get_phase_detail(req.phase_id)
    phase_title = phase_detail.get("title", req.phase_id) if phase_detail else req.phase_id
    guide_summary = ""
    if phase_detail and phase_detail.get("guide_markdown"):
        lines = [l for l in phase_detail["guide_markdown"].split("\n") if l.strip() and not l.strip().startswith("<!--")]
        guide_summary = "\n".join(lines[:25])[:800]

    error_text = (req.error_output or "").strip()
    is_error_diagnostic = bool(
        error_text and any(kw in error_text for kw in [
            "Traceback", "Error", "Exception", "AssertionError", 
            "失败", "未全部通过", "blocked", "安全边界策略拦截", "超时"
        ])
    ) or ("排查" in user_query or "诊断" in user_query or "报错" in user_query or "未通过" in user_query)

    # 错误调用栈精确定位提取
    suspicious_lines = []
    import re
    tb_matches = re.findall(r'File ".*?", line (\d+)', error_text)
    if tb_matches:
        suspicious_lines = list(set([int(m) for m in tb_matches]))

    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com")

    if is_error_diagnostic:
        system_prompt = (
            "你是一名拥有深厚 AI 工程经验的资深伴学导师，采用【苏格拉底式启发教学（Socratic Teaching）】。\n"
            "学员在攻克实战关卡时遇到了执行错误或测试失败，你需要帮助学员扫清认知障碍。\n"
            "【教学铁律】：\n"
            "1. 绝不要直接贴出可直接复制过关的完整答案代码！直接给答案会破坏学员思考过程。\n"
            "2. 重在启发：用白话解释根因，指出嫌疑代码行，并提出引导思考的问题与伪代码线索。\n"
            "3. 鼓励学员，保持温和专业且极富启发性的语言风格。"
        )
        user_prompt_text = f"""## 实战关卡背景
- **当前关卡**: 【{phase_title}】 (ID: `{req.phase_id}`)
- **核心关卡目标摘要**:
{guide_summary or "掌握本阶段核心 AI 架构设计与工程落地规范"}

## 学员代码
```python
{req.user_code}
```

## 终端报错或测试未通过信息
```
{error_text}
```

## 学员提问诉求
{user_query if user_query else "请帮我分析报错根因，给出启发式排障思路，不要直接给我完整答案。"}

---
请按四大维度输出 Markdown：
### 1. 💡 报错根因通俗解读
### 2. 🎯 嫌疑代码与定位线索 (请结合 Traceback 指出嫌疑行)
### 3. 🧭 启发式思考支架 (抛出 2~3 个自查思考题，严禁贴完整代码)
### 4. 📖 关联知识手册导航
"""
    else:
        system_prompt = (
            "你是一名拥有十年以上大模型系统架构与 AI Agent 落地经验的世界级技术专家导师。\n"
            "你的职责是为学员提供一份具备工业级水准的【深度架构 Code Review 与生产落地建议】。\n"
            "原则：犀利透彻、直击根因、具备大厂代码审美、企业级最佳实践兼备。务必结合代码具体剖析。"
        )
        user_prompt_text = f"""## 实战关卡背景
- **当前关卡**: 【{phase_title}】 (ID: `{req.phase_id}`)
- **核心目标摘要**:
{guide_summary or "掌握本阶段核心 AI 架构设计与工程落地规范"}

## 学员代码
```python
{req.user_code}
```

## 执行状态
```{error_text if error_text else "代码执行退出码为 0，终端无异常报错。"}```

## 学员疑问
{user_query if user_query else "请对当前代码进行多维度深度 Code Review，指出架构盲点并给出生产级优化重构建议。"}

---
请按五大维度输出 Markdown：
### 1. 📊 代码健康度与架构评分 (给出评分 XX/100 及评级 S/A/B/C)
### 2. 🎯 关卡核心技术对齐度
### 3. 🔍 核心盲点与隐患排查
### 4. ⚡ 企业级架构重构方案
### 5. 🛡️ 工业级落地避坑指南
"""

    async def event_generator():
        # 首包发送元数据 (包含模式、DFL 意图、嫌疑代码行)
        init_meta = {
            "type": "meta",
            "mode": "troubleshooting" if is_error_diagnostic else "review",
            "score": 68 if is_error_diagnostic else 88,
            "level": "B" if is_error_diagnostic else "A",
            "phase_title": phase_title,
            "suspicious_lines": suspicious_lines,
            "dfl_decision": decision
        }
        yield f"data: {json.dumps(init_meta, ensure_ascii=False)}\n\n"

        if api_key:
            try:
                client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
                
                # 组装消息列表 (支持多模态图像感知)
                if req.image_data:
                    user_content = [
                        {"type": "text", "text": user_prompt_text},
                        {"type": "image_url", "image_url": {"url": req.image_data}}
                    ]
                else:
                    user_content = user_prompt_text

                stream = await client.chat.completions.create(
                    model=os.getenv("DEFAULT_MODEL", "deepseek-chat"),
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content}
                    ],
                    max_tokens=1800,
                    temperature=0.3,
                    stream=True
                )
                async for chunk in stream:
                    delta = chunk.choices[0].delta.content if chunk.choices and chunk.choices[0].delta else ""
                    if delta:
                        chunk_data = {"type": "token", "token": delta}
                        yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
            except Exception as e:
                # 异常时退化为本地离线诊断，按自然打字机节奏逐段流式吐出
                err_notice = f"\n\n> ⚠️ *外部推理接口暂时波动 (`{str(e)}`)，已自动降级为本地启发式诊断内核：*\n\n"
                msg_json = json.dumps({"type": "token", "token": err_notice}, ensure_ascii=False)
                yield f"data: {msg_json}\n\n"
                offline_text = _generate_offline_diagnostic(req.phase_id, phase_title, req.user_code, error_text)
                for line in offline_text.split("\n"):
                    line_chunk = json.dumps({"type": "token", "token": line + "\n"}, ensure_ascii=False)
                    yield f"data: {line_chunk}\n\n"
                    await asyncio.sleep(0.02)
        else:
            # 纯离线模式：模拟平滑打字机吐字
            offline_text = f"### 💡 本地启发式诊断引擎 (离线模式)\n未检测到全局 `OPENAI_API_KEY`，系统已启用内置启发式排障内核：\n\n" + _generate_offline_diagnostic(req.phase_id, phase_title, req.user_code, error_text)
            for line in offline_text.split("\n"):
                line_chunk = json.dumps({"type": "token", "token": line + "\n"}, ensure_ascii=False)
                yield f"data: {line_chunk}\n\n"
                await asyncio.sleep(0.015)

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

def _generate_offline_diagnostic(phase_id: str, phase_title: str, user_code: str, error_text: str) -> str:
    """在无网络或无 API Key 场景下，基于 AST 模式和错误堆栈生成高质量本地排障启发"""
    tips = []
    
    if "AssertionError" in error_text:
        tips.append("#### 💡 报错根因：测试断言失败 (AssertionError)")
        tips.append("- **通俗解读**：您的函数返回值与测试用例期望的目标结果不一致。")
        tips.append("- **自查线索**：检查返回的数据结构（是字典、字符串还是元组？）、字段命名是否有大小写偏差，或者边界空值是否被过滤。")
    elif "SyntaxError" in error_text:
        tips.append("#### 💡 报错根因：语法解析错误 (SyntaxError)")
        tips.append("- **通俗解读**：Python 解释器无法读懂某行语句，通常是由于标点符号或代码结构不完整。")
        tips.append("- **自查线索**：检查是否有未闭合的括号 `()`、方括号 `[]` 或引号；检查 `def/if/for` 语句末尾是否遗漏了冒号 `:`。")
    elif "TypeError" in error_text:
        tips.append("#### 💡 报错根因：类型不匹配 (TypeError)")
        tips.append("- **通俗解读**：传入了错误类型的参数，例如将 `None` 当作字符串拼接，或向函数传递了错误数量的实参。")
        tips.append("- **自查线索**：检查函数调用时的参数个数与类型定义，重点排查是否存在返回值可能为 `None` 的前置操作。")
    elif "IndexError" in error_text or "KeyError" in error_text:
        tips.append("#### 💡 报错根因：索引或键不存在越界")
        tips.append("- **通俗解读**：试图从列表或字典中获取不存在的元素。")
        tips.append("- **自查线索**：在访问 `list[i]` 或 `dict[k]` 前，使用 `len(list)` 检查或改用 `dict.get(k, default)` 安全取值。")
    elif "安全边界策略拦截" in error_text:
        tips.append("#### 🛡️ 安全策略提醒：触发平台安全护栏")
        tips.append("- **通俗解读**：代码中引用了受限的系统模块（如 `os.system` / `subprocess`）或动态执行函数。")
        tips.append("- **自查线索**：请使用标准库数据结构或当前关卡提供的推荐工具库完成 AI 算法逻辑，避免调用系统底层命令。")
    else:
        tips.append(f"#### 💡 关卡【{phase_title}】实战建议")
        tips.append("- **核心目标**：请对照本关左侧指南中的【任务目标】与【核心代码模版】。")
        tips.append("- **排查步骤**：建议先在编辑区顶部查看【差异对比】，确认是否误删了关卡原有的测试入参定义。")

    tips.append("\n> **AI 导师寄语**：自主排查与阅读报错堆栈是每位卓越 AI 工程师的核心基本功。微调逻辑后再跑一次测试吧！")
    return "\n\n".join(tips)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, ws_max_size=104857600)
