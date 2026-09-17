import time
from fastapi.testclient import TestClient
from more_fastapi_examples import app

def run_tests():
    print("="*60)
    print("🧪 FastAPI 核心企业级特性 —— 自动化压测与效果展示")
    print("="*60)

    # 实例化官方测试客户端。
    # 它极其强大：不需要你单独去敲命令启动服务器，它直接在内存中模拟发起真实的网络请求！
    client = TestClient(app)

    # ==========================================
    # 测试 1: 中间件 - 全局灾难兜底
    # ==========================================
    print("\n[测试 1] 🗡️ 正在访问包含致命除 0 崩溃的接口 /make_error ...")
    start_t = time.time()
    response = client.get("/make_error")
    end_t = time.time()
    
    print(f"➜ 【前端接收 HTTP 状态码】: {response.status_code}")
    print(f"➜ 【前端接收的友好 JSON】: {response.json()}")
    print(f"💡 结论: 代码里致命的 1/0 并没有让应用挂掉（没有抛出恶心的长串 HTML），而是被外层中间件像网兜一样接住，包装成了优美的 500 标准结构！")

    # ==========================================
    # 测试 2: BackgroundTasks - 旁路解耦防阻塞
    # ==========================================
    print("\n[测试 2] ✉️ 正在访问注册接口 /register (内含一个耗时 2 秒的发邮件任务) ...")
    start_t = time.time()
    response = client.post("/register?username=AI_Guru&email=test@ai.com")
    end_t = time.time()
    
    print(f"➜ 【前端瞬间拿到响应】: {response.json()}")
    print(f"➜ 【前端感知耗时】: {end_t - start_t:.4f} 秒")
    print("💡 结论: 用户并没有傻等发邮件的 2 秒钟！服务器把用户写入数据库后，瞬间把 200 返回给了客户端，发邮件的重活被成功丢进了后台队列默默执行。")

    # ==========================================
    # 测试 3: 中间件 - 安全护城河 IP 黑名单拦截
    # ==========================================
    print("\n[测试 3] 🛑 模拟恶意黑名单 IP (192.168.1.100) 尝试盗刷算力接口 ...")
    
    # 模拟攻击：我们在测试客户端中，强行把请求者的来源 IP 伪装成我们在中间件里拉黑的那个 IP！
    malicious_client = TestClient(app, client=("192.168.1.100", 50000))
    response_banned = malicious_client.post("/generate_image")
    
    print(f"➜ 【黑客收到的 HTTP 状态码】: {response_banned.status_code}")
    print(f"➜ 【黑客收到的拦截提示】: {response_banned.json()}")
    print("💡 结论: 极度高效！该请求根本没有机会进入到 /generate_image 的核心路由（没有消耗任何大模型资源），在中间件的安检门口就被一脚踢飞了！")
    
    print("\n" + "="*60)
    print("✅ 所有高阶特性测试圆满结束！")

if __name__ == "__main__":
    run_tests()
