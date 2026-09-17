import time
import random
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

load_dotenv()

# 初始化模型（在实际生产中，这里会配置两个不同的模型接口）
# 例如：small_model = ChatOpenAI(model="gpt-4o-mini")
#      large_model = ChatOpenAI(model="gpt-4o")
# 为了确保演示能顺利运行，我们暂时都指向同一个可用的模型，仅在逻辑和提示上进行区分
small_model = ChatOpenAI(model="deepseek-v4-flash", temperature=0.7)
large_model = ChatOpenAI(model="deepseek-v4-flash", temperature=0.1)

def classify_complexity(query: str) -> str:
    """
    第一层：请求复杂度分类器 (Router)
    核心降本思路：不要一上来就用最贵的模型！
    """
    # 启发式规则 1：长度
    if len(query) < 15:
        return "simple"
        
    # 启发式规则 2：复杂意图关键词拦截
    complex_keywords = ["分析", "推导", "总结", "逻辑", "财报", "代码", "框架"]
    if any(kw in query for kw in complex_keywords):
        return "complex"
        
    # 如果判断不了，默认降级到小模型（激进降本），或者默认升级到大模型（保质量）
    return "simple"

def handle_request(query: str):
    print(f"\n" + "="*50)
    print(f"👤 用户请求: {query}")
    
    start_time = time.time()
    
    # 【步骤 1：执行路由判别】
    complexity = classify_complexity(query)
    
    # 【步骤 2：动态分发请求】
    if complexity == "simple":
        print(f"🔀 路由判定: [简单请求] -> 分配给 🚀 小模型 (低延迟、低成本)")
        # 小模型直接回答
        response = small_model.invoke([HumanMessage(content=query)])
        cost_level = "1x (极低)"
        
    elif complexity == "complex":
        print(f"🔀 路由判定: [复杂请求] -> 分配给 🧠 大模型 (高算力、深逻辑)")
        # 复杂任务可以结合前面学过的 CoT 提示词
        enhanced_query = f"请一步步仔细思考，并详细分析：{query}"
        response = large_model.invoke([HumanMessage(content=enhanced_query)])
        cost_level = "30x (高)"

    end_time = time.time()
    
    # 展示结果
    print("-" * 50)
    content = response.content.replace('\n', ' ')
    # 如果输出太长，只截取前 100 个字符展示
    display_content = content if len(content) < 100 else content[:100] + "..."
    print(f"🤖 模型回复: {display_content}")
    print(f"⏱️ 耗时: {end_time - start_time:.2f}s | 💰 成本倍率: {cost_level}")

if __name__ == "__main__":
    test_queries = [
        "你好，今天天气不错",
        "帮我翻译：Hello World",
        "公司财报显示连续三年亏损，但研发投入逐年上升了30%，请分析其背后的商业逻辑，并推导未来的存活率。"
    ]
    
    for q in test_queries:
        handle_request(q)
