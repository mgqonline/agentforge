import os
from typing import Annotated
from typing_extensions import TypedDict
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# 1. 定义物理工具箱 (Acting 的基础)
# ==========================================
@tool
def get_weather(location: str) -> str:
    """获取指定城市的实时天气信息。当你需要回答天气时必须调用此工具。"""
    weather_db = {
        "北京": "晴天，微风，气温 25度",
        "上海": "阴有阵雨，气温 18度",
        "纽约": "多云，气温 20度"
    }
    return weather_db.get(location, "对不起，无法获取该城市天气")

@tool
def calculate_travel_time(distance: float, speed: float) -> str:
    """计算两地旅行所需的时间，参数为物理距离（公里）和交通工具速度（公里/小时）。"""
    if speed <= 0:
        return "速度必须大于0"
    hours = round(distance / speed, 2)
    return f"预计需要 {hours} 小时"

# ==========================================
# 2. 核心架构与运行 (纯原生 StateGraph 构建)
# ==========================================

# A. 定义图的状态流转数据结构
class State(TypedDict):
    # 使用 add_messages 表示在这个状态中，messages 列表是不断追加追加累积的（历史记录机制）
    messages: Annotated[list[BaseMessage], add_messages]

def run_react_agent():
    print("=== ReAct Agent 实战演示 (原生 StateGraph 最新架构) ===\n")
    
    model = ChatOpenAI(model="deepseek-v4-flash", temperature=0)
    tools = [get_weather, calculate_travel_time]
    
    # 强制将工具的能力与结构绑定给大模型
    model_with_tools = model.bind_tools(tools)
    
    # B. 定义大脑思考节点
    def call_model(state: State):
        # 将历史对话信息发给模型，由模型产生 "自然语言回复" 或 "工具调用指令(Action)"
        response = model_with_tools.invoke(state["messages"])
        
        # 拦截并在控制台输出思维链，便于观察
        if response.tool_calls:
            print("🤔 [Thought]: 模型认为当前信息不足，思考后决定必须调用工具。")
            for t in response.tool_calls:
                print(f"🛠️  [Action]: 决定调用外部函数 '{t['name']}', 传入参数: {t['args']}")
        else:
            print("🧠 [Thought]: 所有信息收集完毕，进行最终整理汇总。")
            
        # 返回的状态会被 add_messages 自动追加到总的 messages 列表里
        return {"messages": [response]}

    # C. 原生构建状态机图 (StateGraph)
    workflow = StateGraph(State)
    
    # 注入节点：一个是思考节点 (agent)，一个是执行外部工具节点 (tools)
    workflow.add_node("agent", call_model)
    # ToolNode 是官方提供的轻量级封装，它能自动解析模型输出的 tool_calls 并执行对应的 Python 物理函数
    workflow.add_node("tools", ToolNode(tools)) 
    
    # D. 连线与路由规则 (ReAct 循环的核心本质)
    workflow.add_edge(START, "agent")  # 所有的入口都必须先经过大脑思考
    
    # 条件路由：检查 agent 的输出
    # 如果输出里包含了 tool_calls，tools_condition 会将流向指派给 "tools" 节点。
    # 否则，它会将流向指派给 END，代表彻底完成任务退出。
    workflow.add_conditional_edges("agent", tools_condition)
    
    # 执行完外部工具后，必须强制连线回 "agent" 节点，让大脑对执行结果进行再度审视！
    workflow.add_edge("tools", "agent") 
    
    # 编译成最终可执行的应用图
    app = workflow.compile()
    
    query = (
        "我现在身处北京，我打算去一个距离北京 1200 公里的城市出差。"
        "我坐的高铁速度大概是 300 公里/小时。请问我出发地的天气怎么样？"
        "并且请帮我计算一下在路上的时间。"
    )
    
    print(f"👤 用户下达复杂任务:\n{query}\n")
    print("-" * 50)
    print("🔄 开始执行原生状态图 ReAct 循环")
    print("-" * 50)
    
    # 执行状态图，打印工具执行的 Observation
    for chunk in app.stream({"messages": [("user", query)]}):
        if "tools" in chunk:
            # 只有当路由走向了 tools 节点，我们才会拦截并打印物理执行结果
            messages = chunk["tools"]["messages"]
            for msg in messages:
                print(f"👀 [Observation]: 工具执行完毕，获取外部数据 -> {msg.content}")
            print() # 空行分隔
            
    print("-" * 50)
    print("🏁 [Final Answer]: 最终结果输出")
    print("-" * 50)
    
    final_state = app.invoke({"messages": [("user", query)]})
    print(final_state["messages"][-1].content)

if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        print("请在 .env 文件中设置 OPENAI_API_KEY")
    else:
        run_react_agent()
