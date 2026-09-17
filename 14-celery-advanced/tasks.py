import time
import random
from celery_app import app
from celery import chord, chain

# =====================================================================
# 场景 1：基础耗时任务与 LLM 异常重试策略
# 痛点：大模型 API 非常容易报 429 (Too Many Requests) 或 502。
# 解法：开启 max_retries，并使用自适应指数退避算法进行重试。
# =====================================================================
@app.task(bind=True, max_retries=3)
def generate_report(self, topic: str):
    print(f"🚀 [Worker] 开始为 '{topic}' 查阅资料并生成万字研报...")
    time.sleep(2) # 模拟大模型疯狂吐 Token
    
    # 模拟大模型 API 突然抽风限流报错
    if random.random() < 0.4:
        print(f"⚠️ 触发大模型 API 限流！启动第 {self.request.retries + 1} 次自动退避重试...")
        # countdown = 2 ** self.request.retries：意味着第一次等 1 秒重试，第二次等 2 秒，第三次等 4 秒。
        # 这是高并发下极其经典的防雪崩“指数退避算法”！
        raise self.retry(exc=Exception("LLM API 429 Too Many Requests"), countdown=2 ** self.request.retries)
        
    return f"✅ '{topic}' 的研报生成完毕！"

# =====================================================================
# 场景 2：多智能体协作 (Map-Reduce 编排)
# 痛点：你需要查苹果、微软、谷歌三家公司的财报。如果让一个 Agent 顺序去查，太慢了！
# 解法：Celery 的 Chord 原语！派 3 个 SubAgent (子任务) 同时去查，
# 所有人全部查完后，把 3 份结果统一汇总给 MainAgent (主任务) 撰写终极报告。
# =====================================================================
@app.task
def subagent_research(topic: str):
    """SubAgent：并行搜索信息"""
    print(f"🔍 [SubAgent] 正在全网检索关于 '{topic}' 的机密财报...")
    time.sleep(2) # 模拟网络搜索耗时
    return f"[{topic} 的机密财务数据]"

@app.task
def mainagent_summarize(results: list, main_topic: str):
    """MainAgent：汇总所有 SubAgent 的心血"""
    print(f"\n🧠 [MainAgent] 所有特工收集完毕！开始汇总 {len(results)} 份子报告...")
    time.sleep(1) # 模拟大模型总结耗时
    summary = " | ".join(results)
    final_output = f"【{main_topic} 终极财报】\n根据收集的数据: {summary}"
    print(final_output)
    return final_output

# =====================================================================
# 场景 3：定时巡检任务 (Cronjob)
# =====================================================================
@app.task
def sync_vector_db():
    print("🔄 [Cronjob] 开始拉取公司最新文档，切块打 Embedding，重新灌入 FAISS 向量库...")
    time.sleep(3)
    return "向量库更新完成"

# =====================================================================
# 【代码实操演示】如何在业务代码（如 FastAPI 接口）中触发上述任务
# =====================================================================
def trigger_demo():
    print("\n" + "="*50)
    print("=== 演示 1: 异步调用大模型防阻塞 ===")
    # 只要加上 .delay()，任务就会瞬间变成一串字节飞进 Redis 队列，主进程完全不卡顿！
    task_id = generate_report.delay("2026 人工智能趋势")
    print(f"✅ 任务已投递入列！排队号码牌: {task_id}")

    print("\n" + "="*50)
    print("=== 演示 2: 多智能体 Chord 并发工作流编排 ===")
    sub_topics = ["苹果财报", "微软财报", "英伟达财报"]
    
    # 💡 语法解析：
    # 1. 列表推导式发起了 3 个完全并行的子任务 (.s 代表 Signature 任务签名，不立刻执行)
    # 2. 大家都跑完后，自动把一个 list 结果塞给 mainagent_summarize 的第一个参数
    workflow = chord(
        (subagent_research.s(t) for t in sub_topics), 
        mainagent_summarize.s("硅谷三巨头 Q1 总结")         
    )
    workflow_id = workflow.delay()
    print(f"✅ 分布式 Agent 协作流已启动！流水号: {workflow_id}")

if __name__ == "__main__":
    trigger_demo()
