import os
from dotenv import load_dotenv
load_dotenv()  # 自动加载根目录下的 .env 文件中的 OPENAI_API_KEY 等环境变量

import operator
from typing import Annotated, TypedDict, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage
from langgraph.graph import StateGraph, END
from langchain_core.tools import tool

# 1. 定义工具 (Tools)
@tool
def get_weather(location: str) -> str:
    """获取指定城市的天气信息"""
    # 真实场景下这里会去请求外部天气 API
    if "北京" in location:
        return "22°C，晴朗，微风"
    elif "上海" in location:
        return "25°C，多云，适合出行"
    elif "长沙" in location:
        return "30°C，雷阵雨，注意防雷"
    else:
        return "未知天气，可能在下钞票雨"

tools = [get_weather]

# 2. 定义 Agent 的状态 (State)
class AgentState(TypedDict):
    # messages 序列会自动把新消息 append 进去 (依赖 operator.add)
    messages: Annotated[List[BaseMessage], operator.add]

# 3. 初始化带有工具调用的 LLM
# 注意：你需要事先在终端或 .env 中设置 OPENAI_API_KEY 和 OPENAI_API_BASE
model_name = os.getenv("MODEL_NAME", "deepseek-v4-pro") # 读取环境变量，默认回退到 DeepSeek
llm = ChatOpenAI(model=model_name, temperature=0)
llm_with_tools = llm.bind_tools(tools)

# 4. 定义节点函数 (Nodes)
def agent_node(state: AgentState):
    """节点：大模型进行思考和决策"""
    print("🤖 [Agent 节点] 大模型正在思考...")
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}

def tool_node(state: AgentState):
    """节点：执行工具"""
    print("🛠️  [Tool 节点] 正在执行工具...")
    last_message = state["messages"][-1]
    
    # 获取 LLM 决定调用的工具及其参数
    tool_calls = last_message.tool_calls
    tool_responses = []
    
    # 我们这里手动实现工具分发逻辑（实际工程中可用 langgraph 提供的 ToolNode）
    for tool_call in tool_calls:
        if tool_call["name"] == "get_weather":
            # 调用函数
            result = get_weather.invoke(tool_call["args"])
            print(f"   执行 get_weather({tool_call['args']}) -> {result}")
            # 把结果封装为 ToolMessage
            tool_responses.append(
                ToolMessage(content=result, tool_call_id=tool_call["id"])
            )
            
    return {"messages": tool_responses}

# 5. 定义路由分支 (Conditional Edges)
def should_continue(state: AgentState) -> str:
    """决定下一步去哪里：是去执行工具，还是结束对话？"""
    last_message = state["messages"][-1]
    
    # 如果大模型决定调用工具，就走向 "action" 分支
    if last_message.tool_calls:
        return "continue"
    # 如果不需要调用工具了，直接返回给用户，图执行结束
    return "end"

# 6. 编排并编译图 (Graph)
workflow = StateGraph(AgentState)

# 添加节点
workflow.add_node("agent", agent_node)
workflow.add_node("action", tool_node)

# 设置起点
workflow.set_entry_point("agent")

# 添加条件边：从 agent 节点出发，根据 should_continue 决定下一步
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "continue": "action",
        "end": END
    }
)

# 添加普通边：工具执行完后，必须跳回 agent 节点让大模型看结果
workflow.add_edge("action", "agent")

# 编译成可运行的应用
app = workflow.compile()

# 7. 测试运行
if __name__ == "__main__":
    print("========== 启动 LangGraph 智能体 ==========")
    user_input = "北京和长沙的天气分别怎么样？"
    print(f"👤 用户：{user_input}\n")
    
    # 注入初始状态
    initial_state = {"messages": [HumanMessage(content=user_input)]}
    
    # 流式输出图的执行过程
    final_messages = []
    for output in app.stream(initial_state):
        # 抓取每个节点运行后的最新状态 (output 的 value)
        for node_name, node_state in output.items():
            final_messages = node_state.get("messages", [])
        
    print("\n========== 最终回答 ==========")
    # 打印对话记录中最新的一条消息内容
    if final_messages:
        print(final_messages[-1].content)
