import os
import json
import random
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv

load_dotenv()

class PromptManager:
    """
    Prompt 版本管理器
    将 Prompt 视作代码资产，从文件系统中动态加载对应版本的配置。
    """
    def __init__(self, base_dir: str):
        self.base_dir = base_dir

    def load_version(self, version: str) -> Dict[str, Any]:
        """加载特定版本的 Prompt 框架 (分层加载)"""
        v_dir = os.path.join(self.base_dir, version)
        if not os.path.exists(v_dir):
            raise ValueError(f"Version {version} not found.")

        # 1. 加载 System Prompt (系统级设定)
        with open(os.path.join(v_dir, "system.prompt"), "r", encoding="utf-8") as f:
            system_prompt = f.read().strip()

        # 2. 加载 Task Prompt (任务执行与参数模板)
        with open(os.path.join(v_dir, "task.prompt"), "r", encoding="utf-8") as f:
            task_prompt = f.read().strip()

        # 3. 加载 示例库 (Few-shot)
        with open(os.path.join(v_dir, "examples.json"), "r", encoding="utf-8") as f:
            examples = json.load(f)

        return {
            "system": system_prompt,
            "task": task_prompt,
            "examples": examples
        }

    def build_messages(self, version: str, kwargs: Dict[str, str]) -> List:
        """组装 LangChain Messages"""
        prompt_data = self.load_version(version)
        messages = []

        # 放入 System
        messages.append(SystemMessage(content=prompt_data["system"]))

        # 放入 示例库 (Few-shot)
        for ex in prompt_data["examples"]:
            # 格式化示例的输入
            ex_input_formatted = prompt_data["task"].format(**ex["input"])
            messages.append(HumanMessage(content=ex_input_formatted))
            messages.append(SystemMessage(content=ex["output"])) # 用 System/AI 模拟助手回答

        # 放入 真实的当前任务 (参数注入)
        current_task = prompt_data["task"].format(**kwargs)
        messages.append(HumanMessage(content=current_task))

        return messages


class PromptABTester:
    """
    AB 测试 / 灰度发布网关
    根据配置的权重，决定当前请求路由到哪一个版本的 Prompt
    """
    def __init__(self, routing_rules: Dict[str, float]):
        self.routing_rules = routing_rules

    def select_version(self) -> str:
        """根据权重做灰度路由"""
        rand = random.random()
        cumulative = 0.0
        for version, weight in self.routing_rules.items():
            cumulative += weight
            if rand <= cumulative:
                return version
        return list(self.routing_rules.keys())[0]

def run_demo():
    print("=== Prompt 框架设计与版本管理演示 ===\n")
    
    prompt_dir = os.path.join(os.path.dirname(__file__), "prompts")
    manager = PromptManager(base_dir=prompt_dir)
    
    # 配置灰度发布规则 (v1占20%，v2占80%)
    router = PromptABTester(routing_rules={"v1": 0.2, "v2": 0.8})

    model = ChatOpenAI(model="deepseek-v4-flash", temperature=0.1)

    # 模拟真实用户的请求
    test_kwargs = {
        "context": "退换货规定：影响二次销售不退换。保修：电子产品1年。",
        "query": "你好，我的鼠标摔裂了，按键也不灵了，才买了两个月，能退吗？"
    }

    # 模拟处理 3 次请求，观察路由和输出变化
    for i in range(1, 4):
        print(f"--- [请求 {i}] ---")
        
        # 1. 动态路由挑选 Prompt 版本
        selected_version = router.select_version()
        print(f"📡 灰度路由命中版本: {selected_version}")
        
        # 2. 从“代码库”中加载并组装完整上下文
        messages = manager.build_messages(selected_version, test_kwargs)
        
        # 3. 发送给大模型
        print(f"🤖 正在调用模型...\n")
        response = model.invoke(messages)
        
        print(f"📝 模型回复:\n{response.content}\n")

if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        print("请在 .env 中设置 OPENAI_API_KEY")
    else:
        run_demo()
