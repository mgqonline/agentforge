import time
import asyncio
import functools
from contextlib import contextmanager
from typing import List, AsyncGenerator
from dataclasses import dataclass, field
from pydantic import BaseModel, Field, ValidationError

# ==========================================
# 1. 高阶装饰器 (Decorator) 与 functools.wraps
# 场景：大模型 API 经常因为限流或超时报错，这是一个极其常见的带参数的重试装饰器
# ==========================================
def retry_llm_call(retries: int = 3, delay: float = 1.0):
    def decorator(func):
        # 🚨 极其关键：functools.wraps 能够保留原函数 func 的 __name__ 和 __doc__ 属性
        # 如果不加这个，在 LangChain 定义 Tool 时会因为拿不到原函数描述而报错！
        @functools.wraps(func)  
        def wrapper(*args, **kwargs):
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    print(f"⚠️ [重试 {attempt + 1}/{retries}] 函数 {func.__name__} 失败: {e}")
                    time.sleep(delay)
            raise Exception(f"❌ 最终失败：超过最大重试次数 {retries}")
        return wrapper
    return decorator

@retry_llm_call(retries=3, delay=0.5)
def unstable_api_call():
    """模拟一个极其不稳定的第三方网络请求"""
    import random
    if random.random() < 0.7:
        raise ConnectionError("Connection Timeout")
    return "✅ API 请求成功！"

# ==========================================
# 2. 上下文管理器 (Context Manager)
# 场景：优雅地统计一段代码的执行耗时，或者确保数据库/连接池的安全释放
# ==========================================
@contextmanager
def timer_context(description: str):
    start_time = time.time()
    print(f"⏳ 开始: {description}")
    try:
        # yield 将控制权交还给 with 代码块内部
        yield  
    finally:
        # 无论 with 块内部是否抛出异常，finally 都会绝对执行！保证资源释放
        end_time = time.time()
        print(f"⏱️ 结束: {description} | 耗时: {end_time - start_time:.4f} 秒\n")

# ==========================================
# 3. 异步生成器 (Async Generator)
# 场景：模拟大模型最核心的特性 —— 流式输出 (Streaming)，拒绝让用户干等
# ==========================================
async def mock_llm_stream(prompt: str) -> AsyncGenerator[str, None]:
    """模拟大模型逐个吐出 Token"""
    words = ["我", "是", "一", "个", "流", "式", "输", "出", "的", "A", "I"]
    for word in words:
        await asyncio.sleep(0.1)  # 模拟推断时的网络延迟
        yield word                # 使用 yield 而不是 return

# ==========================================
# 4. Asyncio 并发控制 (gather 与 as_completed)
# 场景：Agent 同时向大模型发送 3 个并行任务，极大缩短整体等待时间
# ==========================================
async def fetch_data(task_id: int, delay: float) -> str:
    print(f"   -> 任务 {task_id} 开始执行 (预计耗时 {delay}s)...")
    await asyncio.sleep(delay)
    return f"结果_{task_id}"

async def demo_asyncio():
    print("=== 演示 4: asyncio 并发控制 ===")
    
    # 场景 A：使用 gather (等待所有人上车，保持原始顺序发车)
    print("【场景 A：gather (保持结果顺序一致)】")
    tasks = [fetch_data(1, 1.5), fetch_data(2, 0.5), fetch_data(3, 1.0)]
    results = await asyncio.gather(*tasks)
    print(f"   🎉 Gather 汇总结果: {results}\n")

    # 场景 B：使用 as_completed (谁先完成谁先发车，极大地提升用户体验)
    print("【场景 B：as_completed (按完成先后顺序流式返回)】")
    tasks_again = [fetch_data(4, 1.5), fetch_data(5, 0.5), fetch_data(6, 1.0)]
    for future in asyncio.as_completed(tasks_again):
        res = await future
        print(f"   ⚡ 率先抢答: {res}")
    print()

# ==========================================
# 5. Dataclass vs Pydantic
# 场景：Agent 内部状态传输用 Dataclass，外部接口交互用 Pydantic (防大模型幻觉)
# ==========================================

@dataclass
class AgentState:
    """普通的 Dataclass：轻量，适合内部对象封装，但不具备严格的类型强制转换校验能力"""
    query: str
    retry_count: int = 0
    # 必须使用 default_factory 防止所有实例共享同一个 list 引用
    history: List[str] = field(default_factory=list) 

class UserProfile(BaseModel):
    """Pydantic 模型：极其强悍的校验引擎！AI Agent 定义 Tool Schema 的绝对核心规范"""
    user_id: int
    name: str = Field(..., min_length=2, max_length=10, description="用户姓名")
    age: int = Field(..., ge=0, le=120, description="年龄必须在 0 到 120 之间")

def demo_pydantic():
    print("=== 演示 5: Pydantic 强校验与拦截 ===")
    print("假设大模型幻觉了，把年龄写成了负数，把 user_id 写成了字符串...")
    try:
        user = UserProfile(user_id="10086", name="A", age=-5) 
    except ValidationError as e:
        print("🚨 Pydantic 成功拦截了非法数据！报错详情：")
        for err in e.errors():
            print(f"   - 字段 '{err['loc'][0]}': {err['msg']}")

# ==========================================
# 汇总运行
# ==========================================
async def main():
    print("=== 演示 1: 装饰器 (超时重试机制) ===")
    try:
        res = unstable_api_call()
        print(f"最终结果: {res}\n")
    except Exception as e:
        print(e, "\n")
        
    print("=== 演示 2: 上下文管理器 (计时器) ===")
    with timer_context("执行超大文档的向量计算"):
        time.sleep(0.3)
        
    print("=== 演示 3: 异步生成器 (流式打字机效果) ===")
    print("🤖 大模型响应: ", end="", flush=True)
    async for token in mock_llm_stream("你好"):
        print(token, end="", flush=True)
    print("\n\n")
    
    await demo_asyncio()
    demo_pydantic()

if __name__ == "__main__":
    asyncio.run(main())
