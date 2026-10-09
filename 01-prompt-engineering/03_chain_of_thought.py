import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

# 加载环境变量
load_dotenv()

def run_cot_practice():
    print("--- Chain of Thought (思维链) 练习 ---")
    
    model = ChatOpenAI(model="deepseek-v4-flash", temperature=0) # 使用 temperature=0 保证逻辑稳定性

    # 一个需要逻辑推理的问题
    puzzle = """
    问题：果篮里有3个苹果，5个香蕉。小明拿走了2个苹果，又放回了1个香蕉。
    然后小红拿走了所有香蕉，并放回了2个苹果。
    最后，小明又拿走了1个苹果。
    请问现在果篮里分别有多少个苹果和香蕉？
    """

    # 1. 直接回答 (Zero-shot)
    print("\n>>> 实验 A: 直接回答 (无思维链引导)")
    messages_a = [
        SystemMessage(content="你是一个数学助手，请直接给出最终答案。"),
        HumanMessage(content=puzzle)
    ]
    response_a = model.invoke(messages_a)
    print(f"回答:\n{response_a.content}")

    # 2. 思维链引导 (Chain of Thought)
    print("\n>>> 实验 B: 思维链引导 (要求逐步思考)")
    messages_b = [
        SystemMessage(content="你是一个逻辑严密的数学助手。在给出最终答案之前，请务必详细写出你的思考步骤，确保每一步的变化都清晰记录。"),
        HumanMessage(content=puzzle)
    ]
    response_b = model.invoke(messages_b)
    print(f"回答:\n{response_b.content}")

if __name__ == "__main__":
    # 沙箱安全边界禁止读取 OPENAI_API_KEY 等凭据变量，这里不再做前置校验；
    # ChatOpenAI 会自动从环境变量读取密钥，缺失时会抛出明确的鉴权错误。
    run_cot_practice()
