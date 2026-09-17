import time
import asyncio
from typing import AsyncGenerator
from fastapi import FastAPI, Request, Depends, BackgroundTasks, HTTPException

# ==========================================
# 1. Lifespan 生命周期管理
# 场景：启动时加载几块 GPU 显存里的大模型，关闭时安全释放内存。
# （以前用 @app.on_event("startup")，现已被官方废弃，强烈推荐 Lifespan）
# ==========================================
ml_models = {}

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    print("\n🚀 [Lifespan] 启动服务：正在加载数十GB的深度学习模型 (模拟耗时 2秒)...")
    await asyncio.sleep(2)
    ml_models["llm"] = "Super-AI-Model-v1"
    print("✅ [Lifespan] 模型加载完成，API 端口就绪！\n")
    
    yield  # 把控制权交还给 FastAPI，开始挂起处理外网来的 HTTP 请求
    
    print("\n🛑 [Lifespan] 接收到 Ctrl+C 关闭信号：正在清理显存与释放模型...")
    ml_models.clear()
    print("✅ [Lifespan] 资源释放完毕，安全关机。\n")

app = FastAPI(lifespan=lifespan)

# ==========================================
# 2. 中间件 Middleware (@app.middleware)
# 场景：无侵入式地拦截所有请求。比如统计全站 API 响应耗时，或者做全局黑名单 IP 拦截。
# ==========================================
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    
    # 往下走，交给后面真正的具体的路由处理函数 (比如 /generate_report)
    response = await call_next(request)
    
    # 当路由函数处理完后，再返回到这里
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    print(f"👁️ [Middleware] 监测到针对 {request.url.path} 的访问，总链路耗时: {process_time:.4f} 秒")
    return response

# ==========================================
# 3. 嵌套 Depends 依赖树 (Dependency Injection)
# 场景：极其优雅的权限验证流转，防止在每个接口里写重复的 if-else
# ==========================================
async def verify_token(token: str = "Bearer secret_admin_token"):
    """依赖 1：验证最基础的 HTTP Header Token 格式"""
    if not token.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Token Format")
    return token.split(" ")[1]

async def get_current_user(token: str = Depends(verify_token)):
    """依赖 2：嵌套了依赖1。拿到清洗后的 token，去数据库查出具体的用户身份"""
    if token != "secret_admin_token":
        raise HTTPException(status_code=403, detail="Unauthorized")
    return {"user_id": 1024, "role": "admin"}

async def get_db_session(user: dict = Depends(get_current_user)):
    """依赖 3：嵌套了依赖2。拿到用户身份后，给他分配对应的算力池或数据库连接"""
    print(f"🔑 [Depends 验证树] 已授权用户 ID:{user['user_id']}，为其分配高级 VIP 算力队列。")
    return f"DB_Session_For_User_{user['user_id']}"

# ==========================================
# 4. 路由与 BackgroundTasks 异步任务
# 场景：让大模型生成一篇万字研报极其耗时（可能需一分钟）。如果你不把它塞进后台任务，
# 用户的浏览器前端页面就会一直卡着转圈圈，直到超时崩溃。
# ==========================================
def write_long_report_task(user_id: int, topic: str):
    """一个极其阻塞耗时的后台任务"""
    print(f"⚙️ [Background Task] 开始为用户 {user_id} 后台偷偷生成关于 '{topic}' 的研报...")
    time.sleep(3) # 模拟繁重的 CPU 密集型运算
    print(f"✅ [Background Task] 研报 '{topic}' 生成完毕，已推送至用户 {user_id} 的客户端！")

@app.post("/generate_report")
async def generate_report(
    topic: str,
    background_tasks: BackgroundTasks, 
    db_session: str = Depends(get_db_session)  # 在这里触发整个三级嵌套验证树
):
    """前端调用该接口后会瞬间拿到 200 返回，真正的重活交给了后台线程池"""
    
    # 1. 将耗时任务扔进后台队列
    background_tasks.add_task(write_long_report_task, user_id=1024, topic=topic)
    
    # 2. 利用 lifespan 启动时注入的全局资源模型
    model_used = ml_models.get("llm", "Unknown")
    
    # 3. 瞬间响应给用户
    return {
        "status": "Task Accepted",
        "message": f"已经为您分配大模型 {model_used}，研报正在后台火速生成中...",
        "db_in_use": db_session
    }

if __name__ == "__main__":
    import uvicorn
    # 为了方便你测试，直接在脚本内以 8080 端口启动
    uvicorn.run(app, host="127.0.0.1", port=8080)
