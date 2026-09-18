import os
import sqlite3
from typing import Optional
from langchain_core.tools import tool
from pydantic import BaseModel, Field

# ==========================================
# 模拟拓维信息内部数据库环境准备
# ==========================================
def setup_mock_db():
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, role TEXT, salary INTEGER)")
    cursor.execute("INSERT INTO users VALUES (1, '张三', '研究员', 30000)")
    cursor.execute("INSERT INTO users VALUES (2, '李四', '架构师', 45000)")
    cursor.execute("INSERT INTO users VALUES (3, '王五', '测试员', 20000)")
    conn.commit()
    return conn

mock_conn = setup_mock_db()

# ==========================================
# ❌ 反面教材：不安全的插件设计 (LLM07) & 提示词注入隐患 (LLM01)
# ==========================================
# 危险点 1：允许大模型直接拼接底层查询语句 (容易被提示词注入修改意图)
# 危险点 2：缺少参数类型的强限制
@tool("Insecure_DB_Query")
def insecure_query(sql_statement: str) -> str:
    """
    一个极其危险的工具。
    输入是一个完整的 SQL 查询语句，工具会直接执行它并返回结果。
    """
    print(f"[警告] 正在执行无保护的 SQL: {sql_statement}")
    try:
        cursor = mock_conn.cursor()
        # ⚠️ 危险动作：直接执行大模型生成的 SQL。
        # 如果大模型被恶意提示词注入，生成了 DROP TABLE 或 UPDATE 语句，数据库将被破坏。
        cursor.execute(sql_statement)
        results = cursor.fetchall()
        return str(results)
    except Exception as e:
        return f"查询出错: {e}"

# ==========================================
# ✅ 正面教材：安全的插件设计与注入防护
# ==========================================
# 防护点 1：使用 Pydantic 强校验输入参数，杜绝大模型随意发挥
class SecureUserQuerySchema(BaseModel):
    user_id: int = Field(description="必须是数字类型的员工 ID，如 1, 2, 3")

# 防护点 2：工具内部收敛底层逻辑，只暴露安全的业务接口给大模型
@tool("Secure_User_Query", args_schema=SecureUserQuerySchema)
def secure_query(user_id: int) -> str:
    """
    安全的查询工具。
    只需传入员工的数字 ID，即可查询其信息。
    """
    print(f"[安全审查] 拦截非法输入，放行合法查询参数: user_id={user_id}")
    try:
        cursor = mock_conn.cursor()
        # ✅ 安全动作：使用参数化查询 (Parameterized Query) 防御任何形式的 SQL 注入。
        # 大模型不再具备拼接 SQL 的权限，只能提供一个单纯的整数。即使被提示词注入，最多也只能查询其他人的信息，无法破坏数据库。
        cursor.execute("SELECT name, role FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        if result:
            return f"员工姓名: {result[0]}, 职位: {result[1]}"
        return "未找到该员工。"
    except Exception as e:
        return f"查询出错: {e}"

if __name__ == "__main__":
    print("======== 拓维信息安全沙箱演示 ========\n")
    
    # 模拟攻击场景：大模型被提示词注入诱导，生成了危险指令
    malicious_output_from_llm = "DROP TABLE users;"
    print("💥 【模拟不安全工具调用】")
    res1 = insecure_query.invoke({"sql_statement": malicious_output_from_llm})
    print(f"执行结果: {res1}\n")
    
    # 模拟安全场景：即使大模型被诱导，安全工具也无法被攻破
    print("🛡️ 【模拟安全工具调用】")
    try:
        # Pydantic 拦截：如果传入的是非整数或者恶意指令，在进入业务逻辑前就会报错
        res2 = secure_query.invoke({"user_id": 1})
        print(f"执行结果: {res2}")
    except Exception as e:
        print(f"安全网关拦截: {e}")
