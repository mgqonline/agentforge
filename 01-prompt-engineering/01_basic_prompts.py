import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

# 加载环境变量
load_dotenv()

def run_basic_prompt():
    print("--- 基础 Prompt 示例 ---")
    
    # 初始化模型 (配置 DeepSeek 标准模型并设置合理 max_tokens 保证秒级响应)
    model = ChatOpenAI(
        model=os.getenv("DEFAULT_MODEL", "deepseek-chat"),
        max_tokens=300,
        temperature=0.7
    )
    
    # 角色定义列表
    roles = [
        {
            "name": "鲁迅风格评论家",
            "system": "你是一位鲁迅风格的文学评论家，说话简洁、犀利、富有哲理。",
            "human": "评价一下现代人对手机的依赖。"
        },
        {
            "name": "极客程序员",
            "system": "你是一个只会用 Python 代码回答问题的极客程序员。严禁使用任何自然语言解释，只能输出可执行的代码或注释。",
            "human": "如何向女朋友解释什么是异步编程？"
        },
        {
            "name": "毒舌健身教练",
            "system": "你是一个非常毒舌且严厉的健身教练。你对那些找借口不运动的人极度不满，说话充满了讽刺和鞭策。",
            "human": "教练，我今天加班太累了，能不能不练腿了？"
        }
    ]

    for role in roles:
        print(f"\n>>> 角色测试: {role['name']}")
        messages = [
            SystemMessage(content=role['system']),
            HumanMessage(content=role['human'])
        ]
        response = model.invoke(messages)
        print(f"设定: {role['system']}")
        print(f"输入: {role['human']}")
        print(f"模型输出:\n{'-'*20}\n{response.content}\n{'-'*20}")

if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") == "your_api_key_here":
        print("错误: 请在 .env 文件中配置有效的 OPENAI_API_KEY")
    else:
        run_basic_prompt()
