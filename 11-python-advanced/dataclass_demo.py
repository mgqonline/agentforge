from dataclasses import dataclass, field
from typing import List

# ==========================================
# 核心定义
# ==========================================
@dataclass
class AgentState:
    """普通的 Dataclass：轻量，适合内部对象封装，但不具备严格的类型强制转换校验能力"""
    # 必填字段，没有默认值
    query: str
    
    # 带有默认值的不可变类型（int, str, bool 等可以直接写默认值）
    retry_count: int = 0
    
    # 🚨 带有默认值的可变类型（list, dict, set 等），绝对不能写成 = []
    # 必须使用 field(default_factory=list)
    history: List[str] = field(default_factory=list) 

def run_demo():
    print("=== 1. Dataclass 的自动化魔法 ===")
    # 魔法1：自动生成了极其优雅的 __init__ 方法，支持按名传参
    state1 = AgentState(query="帮我写一段 Python 代码")
    
    # 魔法2：自动生成了可读性极强的 __repr__，打印出来非常直观，省去了手写 __str__ 的麻烦
    print(f"初始化的 state1:\n  {state1}")
    
    # 修改状态
    state1.retry_count += 1
    state1.history.append("大模型调用成功")
    print(f"修改后的 state1:\n  {state1}")

    print("\n" + "="*50)
    print("=== 2. 避坑指南：为什么必须用 default_factory？ ===")
    
    # 实例化第二个全新的对象
    state2 = AgentState(query="帮我查询明天的天气")
    print(f"全新的 state2:\n  {state2}")
    print("💡 解析：你可以看到 state2 的 history 是干净的空列表 []。")
    print("如果你在定义类时写成了 `history: List[str] = []`，这在 Python 中叫【默认可变参数陷阱】。")
    print("这会导致内存中只存在一个 list，state1 添加的日志会直接污染并出现在 state2 中！而在并发的 Agent 开发中，这种多会话串库的 Bug 将是毁灭性的。")

    print("\n" + "="*50)
    print("=== 3. 认清边界：缺乏强校验能力 ===")
    print("🚨 现在，我们故意瞎传数据：把 query 传成数字，把 retry_count 传成汉字...")
    
    state_bad = AgentState(query=99999, retry_count="无限次")
    print(f"创建出的畸形 state:\n  {state_bad}")
    print("💡 结论：你看！Dataclass 连眼都不眨一下就创建成功了，它完全无视了你的类型注解！")
    print("这就是为什么 Dataclass 只能用于系统内部（如 LangGraph 的 State，因为内部流转的都是可靠数据）。如果面对不可靠的外部用户输入或大模型输出，必须使用 Pydantic。")

if __name__ == "__main__":
    run_demo()
