import os
from dotenv import load_dotenv
from autogen import AssistantAgent, UserProxyAgent
from autogen.coding import LocalCommandLineCodeExecutor

# 加载环境变量
load_dotenv()

def main():
    # 1. 配置大语言模型 (这里兼容了 standard_agent_builder 中提到的 DeepSeek 代理配置)
    llm_config = {
        "config_list": [
            {
                "model": "deepseek-chat",
                "api_key": os.environ.get("DEEPSEEK_API_KEY"),
                "base_url": "https://api.deepseek.com/v1"
            }
        ],
        "temperature": 0
    }

    # 2. 创建代码助手 Agent (大脑)
    # 它负责根据需求编写代码，并在结束时发出 TERMINATE 信号
    assistant = AssistantAgent(
        name="coder_assistant",
        system_message="""你是一个资深的 Python 代码助手。
你的目标是编写高质量的代码来解决用户的问题。
当你需要执行代码时，请将代码包裹在 ```python 和 ``` 之间。
如果代码执行报错，请分析报错并给出修正后的代码。
当你确信任务已经圆满完成且代码运行无误时，请回复 'TERMINATE' 结束对话。""",
        llm_config=llm_config,
        is_termination_msg=lambda msg: msg.get("content") is not None and "TERMINATE" in msg["content"],
    )

    # 3. 配置本地代码沙盒执行器
    work_dir = "workspace"
    os.makedirs(work_dir, exist_ok=True)
    
    code_executor = LocalCommandLineCodeExecutor(
        timeout=10, 
        work_dir=work_dir
    )

    # 4. 创建用户代理 Agent (执行者 / 替身)
    # 它本身不用 LLM，专职负责拦截并执行代码，或者在需要时请求人类输入
    user_proxy = UserProxyAgent(
        name="user_proxy",
        human_input_mode="NEVER",  # 改为 "TERMINATE" 可以让人类在每次轮次结束前选择是否插手
        max_consecutive_auto_reply=10,  # 防止由于报错导致的死循环
        code_execution_config={"executor": code_executor},
        llm_config=False,
        is_termination_msg=lambda msg: msg.get("content") is not None and "TERMINATE" in msg["content"],
    )

    # 5. 启动对话任务
    task_prompt = "请用 Python 写一个简单的函数，生成前20个斐波那契数列数字，并把它保存到 fib.txt 文件中，然后运行这个代码。"
    print(f"=== 启动任务: {task_prompt} ===")
    
    user_proxy.initiate_chat(
        assistant,
        message=task_prompt
    )

if __name__ == "__main__":
    main()
