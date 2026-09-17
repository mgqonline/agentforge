import os
import time
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# 1. Token 精细化管理：上下文压缩与裁剪
# ==========================================
def estimate_tokens(text: str) -> int:
    """估算 Token 数量 (工程简易版：1个中文字符约等于 1.5个 token)
    在真实生产中，应该使用 tiktoken 库进行精确计算。"""
    return int(len(text) * 1.5)

def trim_message_history(messages: list, max_tokens: int = 500) -> list:
    """
    滑动窗口裁剪策略：
    在多轮对话中，Token 很容易爆表。我们的策略是：
    1. 【绝对保底】：永远保留 SystemMessage（系统级设定不能丢）。
    2. 【滑动窗口】：从最新的一条消息开始往前推算，只要不超过最大 Token，就保留。
    3. 超过的部分直接切断，放弃久远的上下文。
    """
    system_msg = [m for m in messages if isinstance(m, SystemMessage)]
    other_msgs = [m for m in messages if not isinstance(m, SystemMessage)]
    
    kept_msgs = []
    # 预留给 System 的 Token
    current_tokens = sum(estimate_tokens(m.content) for m in system_msg)
    
    # 从最新的一条消息开始往前“抢占” Token 额度
    for msg in reversed(other_msgs):
        msg_tokens = estimate_tokens(msg.content)
        if current_tokens + msg_tokens > max_tokens:
            print(f"✂️ 触发 Token 裁剪: 容量已满，丢弃历史消息 -> '{msg.content[:15]}...'")
            break
        kept_msgs.insert(0, msg)
        current_tokens += msg_tokens
        
    return system_msg + kept_msgs

# ==========================================
# 2. 限流熔断：降级与兜底预案
# ==========================================
def run_with_fallback(messages: list):
    """
    生产级降级方案：
    主模型（贵、慢、容易被限流） -> 备用模型（便宜、稳定） -> 终极兜底（静态话术返回）
    """
    print("\n🚀 开始调用 AI 服务...")
    
    # 模拟主服务 (故意配错 base_url 模拟 API 宕机/超时/熔断)
    primary_model = ChatOpenAI(
        model="gpt-4o", 
        base_url="http://localhost:9999/v1", # 模拟宕机的上游服务
        max_retries=0, 
        request_timeout=2
    )
    
    # 备用服务 (稳定可靠的小模型)
    backup_model = ChatOpenAI(
        model="deepseek-v4-flash",
        temperature=0.7
    )
    
    # 利用 LangChain 的 with_fallbacks 实现无缝降级切换
    robust_chain = primary_model.with_fallbacks([backup_model])
    
    try:
        start = time.time()
        # 虽然主服务宕机了，但因为配了 fallback，它会自动重试备用服务
        response = robust_chain.invoke(messages)
        print(f"✅ 请求成功 (耗时: {time.time() - start:.2f}s): {response.content[:80]}...")
    except Exception as e:
        # 当备用服务也全军覆没时的终极静态兜底
        print(f"❌ 所有 AI 链路均不可用。错误日志: {e}")
        print("🔧 触发终极兜底逻辑：向前端返回静态报错文本 -> '系统当前服务繁忙，请稍后再试。'")

if __name__ == "__main__":
    print("=== AI 工程化：Token 管理与服务降级实战 ===\n")
    
    # 场景一：多轮对话导致的 Token 超额
    print("--- 场景 1: Token 历史记录超限裁剪 ---")
    chat_history = [
        SystemMessage(content="你是智能客服助手，必须始终保持礼貌。"),
        HumanMessage(content="[第一天] 你好，帮我查个东西"),
        AIMessage(content="您好！请问需要查询什么？"),
        # 模拟中间有大量无关的废话历史
        HumanMessage(content="中间发生了很多没有营养的对话，比如今天吃了什么，这部分很长很长很长..." * 5),
        AIMessage(content="是的，了解了。"),
        HumanMessage(content="[今天] 话说回来，我要查询我的订单物流！")
    ]
    
    # 故意将最大 Token 卡得很低，观察它是如何截断废话的
    trimmed_msgs = trim_message_history(chat_history, max_tokens=150)
    print(f"\n📊 裁剪前消息数: {len(chat_history)} -> 裁剪后消息数: {len(trimmed_msgs)}\n保留下来的有效上下文：")
    for i, m in enumerate(trimmed_msgs):
        print(f"  [{i}] {type(m).__name__}: {m.content[:30]}...")

    # 场景二：服务宕机的灾难恢复
    print("\n--- 场景 2: 上游模型宕机/限流时的无缝降级 ---")
    run_with_fallback(trimmed_msgs)
