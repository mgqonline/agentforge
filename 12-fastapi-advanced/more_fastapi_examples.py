import time
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI()

# =====================================================================
# 一、 @app.middleware('http') 的高阶应用场景
# 中间件的核心哲学：像“安检门”一样把守着服务器的唯一入口和出口。
# 所有请求必须先经过它，所有响应也必须最后经过它。
# =====================================================================

# 🛡️ 场景 1：全局异常兜底与日志护城河
# 真实痛点：如果你的代码里有个极度隐蔽的 Bug（比如除以 0、空指针），
# 导致服务彻底崩溃抛出 500。如果不加拦截，前端会收到一大堆极其丑陋、暴露服务端代码路径的 HTML 报错页面。
# 解决：用中间件像一个巨大的网兜，兜住所有漏网之鱼的崩溃，强行转换为优美的 JSON。
@app.middleware("http")
async def global_exception_handler(request: Request, call_next):
    try:
        # 放行请求去执行具体的接口逻辑
        response = await call_next(request)
        return response
    except Exception as e:
        # 🚨 一旦下游任何路由发生了代码层面的崩溃（未被 Try Catch 的），这里一定会捕获到！
        print(f"🚨 [全局灾难报警] 接口 {request.url.path} 发生代码崩溃: {str(e)}")
        
        # 强制把错误包装为前端能无脑解析的标准 JSON 结构，避免前端崩溃
        return JSONResponse(
            status_code=500,
            content={"error_code": "SYSTEM_CRASH", "message": "服务器开小差了，攻城狮正在火速抢修"}
        )

# 🛡️ 场景 2：安全拦截与黑名单系统 (IP 限制 / 风控)
# 真实痛点：你发现某个野鸡 IP 在疯狂用爬虫刷你们极其昂贵的大模型接口。
BLACKLIST_IPS = {"192.168.1.100", "10.0.0.5"}

@app.middleware("http")
async def block_blacklisted_ips(request: Request, call_next):
    client_ip = request.client.host
    if client_ip in BLACKLIST_IPS:
        print(f"🛑 [风控系统盾] 成功拦截来自恶意 IP 的请求: {client_ip}")
        # 注意：这里我们没有写 await call_next(request)，意味着直接把它“踢”出去，
        # 根本不给它访问路由（消耗大模型算力）的任何机会！
        return JSONResponse(status_code=403, content={"msg": "Your IP has been banned!"})
    
    # 如果 IP 干净，放行
    return await call_next(request)


# =====================================================================
# 二、 BackgroundTasks 的高阶应用场景
# 异步任务的核心哲学：【旁路解耦】。把与核心业务（用户当前最关心的结果）
# 无关的脏活累活，统统扔到后台，绝对不让用户多等 1 毫秒。
# =====================================================================

# 🚀 场景 1：核心业务完成后的“通知触达”（发邮件/短信）
# 真实痛点：用户注册接口只需要把账号写入数据库（耗时 0.05秒），
# 但“发送激活邮件”需要调用第三方邮件服务器（耗时可能高达 3 秒）。
# 如果写成同步，用户点击注册后要白白看 3 秒的转圈动画，导致极高的跳出率。
def send_email_task(email: str, username: str):
    print(f"\n📧 [后台队列] 正在连接腾讯云 SMTP 服务器...")
    time.sleep(2) # 模拟网络延迟
    print(f"📧 [后台队列] 成功向 {email} 发送欢迎邮件：'你好 {username}！'\n")

@app.post("/register")
async def register_user(username: str, email: str, bg_tasks: BackgroundTasks):
    # 1. 主链路：极速把用户写入数据库 (模拟耗时 0.05s)
    print(f"💾 [主链路] 用户 {username} 数据已落盘入库。")
    
    # 2. 旁路解耦：将发邮件任务扔进后台
    bg_tasks.add_task(send_email_task, email=email, username=username)
    
    # 3. 瞬间返回前端
    return {"msg": "注册成功！系统极速响应。"}


# 🚀 场景 2：AI 算力消耗账单的“延时入账”
# 真实痛点：用户生成了一张图片，他现在极其迫切地想看到图片 url。
# 此时后端还需要把“本次消耗了 500 个算力币”的计费记录写入云端财务报表，
# 财务系统的入账绝不能阻塞用户看图片的体验。
def sync_billing_log(user_id: int, tokens_used: int):
    print(f"\n💰 [后台计费] 正在连接大数据中心，写入算力流水...")
    time.sleep(1)
    print(f"💰 [后台计费] 用户 {user_id} 成功扣减 {tokens_used} 个 Token，流水已归档。\n")

@app.post("/generate_image")
async def generate_image(bg_tasks: BackgroundTasks):
    # 假设图片瞬间生成完毕
    image_url = "https://ai-cdn.com/cat_flying.jpg" 
    
    # 将记账操作丢给后台
    bg_tasks.add_task(sync_billing_log, user_id=888, tokens_used=5000)
    
    return {"image_url": image_url, "msg": "生成完毕，请查收！"}


# =====================================================================
# 测试路由：用来测试第一个全局兜底的中间件
# =====================================================================
@app.get("/make_error")
async def make_error():
    """一个绝对会引发系统崩溃的接口"""
    a = 1 / 0  # 故意除以 0
    return {"msg": "永远执行不到这里"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8083)
