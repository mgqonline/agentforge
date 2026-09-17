import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

# 加载环境变量
load_dotenv()

def run_comparison():
    print("=== Few-shot vs CoT (少样本与思维链) 实战对比 ===")
    
    # 实例化模型
    model = ChatOpenAI(model="deepseek-v4-flash", temperature=0.1)

    # ==========================================
    # 场景 1: Zero-shot (什么都不用)
    # 适用场景: 常识问答、简单的文本分类、机器翻译。模型本身已具备丰富的先验知识。
    # ==========================================
    print("\n--- 场景 1: Zero-shot (零样本) ---")
    print("适用场景: 简单的意图识别或情感分析")
    
    zero_shot_prompt = "请判断以下用户评论的情感倾向（正面/负面/中性）：'这家餐厅的菜品味道很一般，但是服务员态度还算可以。'"
    print(f"User: {zero_shot_prompt}")
    
    response = model.invoke([HumanMessage(content=zero_shot_prompt)])
    print(f"Assistant: {response.content}")

    # ==========================================
    # 场景 2: Few-shot (少样本)
    # 适用场景: 特定格式输出、风格模仿、罕见分类任务。很难用语言清晰描述，用例子最直观。
    # ==========================================
    print("\n--- 场景 2: Few-shot (少样本) ---")
    print("适用场景: 需要特定的输出格式，或者特定的术语转换")
    
    few_shot_messages = [
        SystemMessage(content="你是一个将日常描述转化为专业代码提交信息的助手。"),
        HumanMessage(content="我改了一个bug，导致首页有时候会白屏。"),
        SystemMessage(content="fix(frontend): 修复首页偶发性白屏问题"),
        HumanMessage(content="加了个新功能，用户现在可以用微信扫码登录了。"),
        SystemMessage(content="feat(auth): 新增微信扫码登录功能"),
        HumanMessage(content="把以前乱七八糟的css代码整理了一下，没加新东西。"),
        SystemMessage(content="refactor(style): 重构并优化CSS样式代码"),
        HumanMessage(content="更新了说明文档，加上了怎么部署后端的步骤。")
    ]
    print("User: 更新了说明文档，加上了怎么部署后端的步骤。")
    
    response = model.invoke(few_shot_messages)
    print(f"Assistant (Few-shot 结果): {response.content}")

    # ==========================================
    # 场景 3: CoT (Chain of Thought 思维链)
    # 适用场景: 逻辑推理、数学问题、复杂规划。直接给答案容易错，需要一步步推导。
    # ==========================================
    print("\n--- 场景 3: CoT (思维链) ---")
    print("适用场景: 逻辑推理计算")
    
    math_puzzle = "农场里有鸡和兔子，总共有 35 个头，94 只脚。请问鸡和兔子各有多少只？"
    
    cot_messages = [
        SystemMessage(content="你是一个逻辑严密的助手。请一步一步写出你的计算和推理过程，最后再给出结论。"),
        HumanMessage(content=math_puzzle)
    ]
    print(f"User: {math_puzzle}")
    
    response = model.invoke(cot_messages)
    print(f"Assistant (CoT 推理过程):\n{response.content}")

    # ==========================================
    # 场景 4: Few-shot + CoT (少样本 + 思维链)
    # 适用场景: 极其复杂的定制化推理任务，不仅需要逐步思考，还需要以特定的格式输出中间步骤和结果。
    # ==========================================
    print("\n--- 场景 4: Few-shot + CoT (少样本结合思维链) ---")
    print("适用场景: 需要复杂推理且输出格式严格限制的场景")
    
    complex_messages = [
        SystemMessage(content="你是一个股票分析助手。必须按照给定的格式输出你的思考过程和最终建议。"),
        HumanMessage(content="公司A今天发布了财报，利润同比增长50%，但CEO宣布离职。该买入还是卖出？"),
        SystemMessage(content="【思考过程】1. 利润同比增长50%是重大利好，说明公司业务强劲。2. CEO离职是利空，可能带来管理层动荡。3. 短期内市场情绪可能会受CEO离职影响而波动，但长期基本面向好。\n【建议】持有观望"),
        HumanMessage(content="公司B的竞争对手刚刚发布了一款革命性的新产品，而公司B的同类产品还在研发中，预计需要半年才能上市。该买入还是卖出？")
    ]
    print("User: 公司B的竞争对手刚刚发布了一款革命性的新产品，而公司B的同类产品还在研发中，预计需要半年才能上市。该买入还是卖出？")
    
    response = model.invoke(complex_messages)
    print(f"Assistant (Few-shot + CoT 结果):\n{response.content}")


if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") == "your_api_key_here":
        print("错误: 请在 .env 文件中配置有效的 OPENAI_API_KEY")
    else:
        run_comparison()
