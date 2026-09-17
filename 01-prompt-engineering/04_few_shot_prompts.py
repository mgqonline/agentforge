import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    FewShotChatMessagePromptTemplate,
)

# 加载环境变量
load_dotenv()

def run_few_shot_practice():
    print("--- Few-shot Prompting (少样本学习) 练习 ---")
    
    model = ChatOpenAI(model="deepseek-v4-flash", temperature=0.7)

    # 1. 任务背景：将普通话翻译成“互联网大厂黑话”
    # 示例数据
    examples = [
        {"input": "我们需要把这个产品做大。", "output": "我们需要对该产品进行全方位赋能，通过差异化打法构建行业壁垒，实现业务持续增长。"},
        {"input": "大家一起想个办法。", "output": "我们需要通过头脑风暴，找准痛点进行深度对齐，从而达成共识，寻找最优解。"},
        {"input": "这个事情不归我管。", "output": "该事项不在我的业务边界内，建议通过跨部门协同，找到对应的归口部门进行承接。"},
    ]

    # 2. 实验 A: Zero-shot (直接提问)
    print("\n>>> 实验 A: Zero-shot (无示例)")
    zero_shot_prompt = "请将下面这句话翻译成互联网黑话：\n'我们得赶紧把这个Bug修好，不然用户要跑光了。'"
    response_a = model.invoke(zero_shot_prompt)
    print(f"输入: 我们得赶紧把这个Bug修好，不然用户要跑光了。")
    print(f"模型输出: {response_a.content}")

    # 3. 实验 B: Few-shot (提供示例)
    print("\n>>> 实验 B: Few-shot (提供3个示例)")
    
    # 定义示例模板
    example_prompt = ChatPromptTemplate.from_messages([
        ("human", "{input}"),
        ("ai", "{output}"),
    ])

    # 创建 Few-shot 模板
    few_shot_template = FewShotChatMessagePromptTemplate(
        example_prompt=example_prompt,
        examples=examples,
    )

    # 最终的 Chat Prompt
    final_prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个精通互联网大厂黑话的专家。请模仿给出的示例风格，将用户的输入进行转化。"),
        few_shot_template,
        ("human", "{input}"),
    ])

    # 生成消息并调用
    chain = final_prompt | model
    response_b = chain.invoke({"input": "我们得赶紧把这个Bug修好，不然用户要跑光了。"})
    
    print(f"输入: 我们得赶紧把这个Bug修好，不然用户要跑光了。")
    print(f"模型输出: {response_b.content}")

if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") == "your_api_key_here":
        print("错误: 请在 .env 文件中配置有效的 OPENAI_API_KEY")
    else:
        run_few_shot_practice()
