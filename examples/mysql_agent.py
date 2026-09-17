"""
标准生产级 MySQL Agent 
架构：LangGraph 状态机循环 + DeepSeek 大模型
特性：自动编写 SQL -> 执行检测 -> 出错反思与自我修正 -> 生成自然语言结论
"""
import os
import operator
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.utilities import SQLDatabase
from dotenv import load_dotenv

# 自动加载环境变量 (读取项目根目录的 .env)
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path)

# ==========================================
# 1. 初始化数据库连接 (本地 MySQL 为例)
# ==========================================
# 实际使用时请将 root:password@localhost:3306/db_name 替换为真实的 MySQL 凭证
# 这里仅作骨架演示
DB_URI = os.getenv("MYSQL_URI", "mysql+pymysql://root:123456@localhost:3306/test_db")
try:
    db = SQLDatabase.from_uri(DB_URI)
    schema = db.get_table_info()
except Exception as e:
    schema = "【提示：由于数据库未启动，当前 schema 为模拟】\nCREATE TABLE users (id INT, name VARCHAR(50), age INT);\nCREATE TABLE orders (id INT, user_id INT, amount DECIMAL);"
    db = None

# ==========================================
# 2. 定义 Agent 状态机结构
# ==========================================
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    sql_query: str
    db_result: str
    is_error: bool
    iterations: int

# ==========================================
# 3. 核心节点实现
# ==========================================
def get_llm(temperature=0):
    """适配 DeepSeek 的标准 LLM"""
    return ChatOpenAI(
        model="deepseek-chat",
        base_url="https://api.deepseek.com/v1",
        temperature=temperature
    )

def write_query_node(state: AgentState):
    """【节点1】负责编写 SQL"""
    print("▶ 正在根据需求编写/修正 SQL 语句...")
    llm = get_llm(temperature=0.1)
    
    # 获取历史记录，如果之前有报错，LLM 会看到并修正
    messages = state["messages"]
    question = messages[0].content
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个资深的 MySQL 数据库工程师。请根据以下数据库结构，为用户的提问编写最精确的 SQL 语句。\n"
                   "数据库 Schema:\n{schema}\n"
                   "注意：只返回可以直接运行的纯 SQL 代码，不要返回任何 markdown 标记或解释。"),
        ("human", "我的问题是：{question}\n如果之前报错了，请参考历史消息并修正你的 SQL。")
    ])
    
    # 如果有之前的执行结果或报错，也一并喂给它
    history = "\n".join([m.content for m in messages[1:]])
    context = question + ("\n历史尝试与报错反馈：\n" + history if history else "")
    
    response = (prompt | llm).invoke({"schema": schema, "question": context})
    sql = response.content.strip().replace("```sql", "").replace("```", "").strip()
    
    return {"sql_query": sql, "iterations": state.get("iterations", 0) + 1}

def execute_and_evaluate_node(state: AgentState):
    """【节点2】执行 SQL，并作为反思器评估结果"""
    sql = state["sql_query"]
    print(f"▶ 正在执行 SQL: {sql}")
    
    # 【安全加固】防止 LLM 生成破坏性 SQL (SQL 注入防御)
    import re
    sql_stripped = sql.strip()
    sql_lower = sql_stripped.lower()
    if not re.match(r"^(select|show|describe|desc|explain)\b", sql_lower):
        result = "安全拦截: 只允许执行 SELECT / SHOW / DESCRIBE / EXPLAIN 只读 SQL"
        print(f"⚠️ {result}")
        return {
            "db_result": result,
            "is_error": True,
            "messages": [AIMessage(content=f"执行的 SQL: {sql}\n结果: {result}")]
        }
    if ";" in sql_stripped.rstrip(";"):
        result = "安全拦截: 禁止执行多语句 SQL"
        print(f"⚠️ {result}")
        return {
            "db_result": result,
            "is_error": True,
            "messages": [AIMessage(content=f"执行的 SQL: {sql}\n结果: {result}")]
        }
        
    forbidden_keywords = [r"\bdrop\b", r"\bdelete\b", r"\btruncate\b", r"\bupdate\b", r"\binsert\b", r"\balter\b", r"\bcreate\b", r"\breplace\b", r"\bgrant\b", r"\brevoke\b"]
    for pattern in forbidden_keywords:
        if re.search(pattern, sql_lower):
            result = f"安全拦截: 禁止执行可能修改数据库的危险命令 ({pattern})"
            print(f"⚠️ {result}")
            return {
                "db_result": result,
                "is_error": True,
                "messages": [AIMessage(content=f"执行的 SQL: {sql}\n结果: {result}")]
            }

    
    if db is None:
        # 模拟执行环境
        if "users" in sql.lower():
            result = "[(1, 'Alice', 30), (2, 'Bob', 25)]"
            is_error = False
        else:
            result = "Error: (1146, \"Table 'test_db.unknown' doesn't exist\")"
            is_error = True
    else:
        # 真实执行环境
        try:
            result = str(db.run(sql))
            is_error = False
        except Exception as e:
            result = f"MySQL 执行报错: {str(e)}"
            is_error = True
            print(f"⚠️ 执行出错，准备发起自修正回路: {result}")
            
    return {
        "db_result": result, 
        "is_error": is_error,
        # 将结果存入上下文，如果是报错，写 SQL 的 LLM 就能看见并反思
        "messages": [AIMessage(content=f"执行的 SQL: {sql}\n结果: {result}")]
    }

def router_edge(state: AgentState):
    """【路由边】决定是结束还是重写"""
    if state["is_error"] and state["iterations"] < 3:
        # 发生错误，且重试次数小于 3，打回修改
        return "rewrite"
    # 成功，或者超过重试上限，进入总结环节
    return "finalize"

def finalize_node(state: AgentState):
    """【节点3】把冷冰冰的 DB 数据转化为人类语言"""
    print("▶ 正在对数据结果进行人话总结...")
    llm = get_llm(temperature=0.3)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "请根据用户的提问和数据库查询结果，用自然、专业的口吻给出一个最终回答。如果查询报错且无法修复，请向用户解释原因。"),
        ("human", "用户问题: {question}\n最终查询结果: {result}")
    ])
    
    response = (prompt | llm).invoke({
        "question": state["messages"][0].content,
        "result": state["db_result"]
    })
    
    return {"messages": [AIMessage(content=response.content)]}

# ==========================================
# 4. 编译图工作流
# ==========================================
def build_mysql_agent():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("write_query", write_query_node)
    workflow.add_node("execute_evaluate", execute_and_evaluate_node)
    workflow.add_node("finalize", finalize_node)
    
    workflow.set_entry_point("write_query")
    workflow.add_edge("write_query", "execute_evaluate")
    
    # 核心：反思循环
    workflow.add_conditional_edges(
        "execute_evaluate",
        router_edge,
        {
            "rewrite": "write_query",
            "finalize": "finalize"
        }
    )
    workflow.add_edge("finalize", END)
    
    return workflow.compile()

# ==========================================
# 5. 测试入口
# ==========================================
if __name__ == "__main__":
    # 注意：运行此脚本需安装 pip install pymysql langchain_community
    print("🚀 初始化 MySQL 反思 Agent 完毕...")
    app = build_mysql_agent()
    
    # 测试问题
    # question = "帮我查一下系统里有哪些用户，以及他们的年龄？"
    question = "帮我查一下系统里有哪些表，各个表的大小？"
    print(f"\n👨‍💻 用户提问: {question}\n")
    
    result = app.invoke({
        "messages": [HumanMessage(content=question)],
        "iterations": 0
    })
    
    print("\n🤖 最终回答:\n", result["messages"][-1].content)
