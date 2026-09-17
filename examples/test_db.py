import os
import pymysql
from dotenv import load_dotenv

load_dotenv()

db_host = os.getenv("DB_HOST", "127.0.0.1")
db_port = int(os.getenv("DB_PORT", 3306))
db_user = os.getenv("DB_USER", "root")
db_pass = os.getenv("DB_PASS", "123456")
db_name = os.getenv("DB_NAME", "test_db")

print(f"尝试连接数据库 {db_host}:{db_port}/{db_name} ...")

try:
    conn = pymysql.connect(
        host=db_host,
        port=db_port,
        user=db_user,
        password=db_pass,
        database=db_name,
        charset='utf8mb4'
    )
    cursor = conn.cursor()
    
    # 测试 1：获取版本
    cursor.execute("SELECT VERSION();")
    version = cursor.fetchone()
    print(f"✅ 数据库连接成功！MySQL 版本: {version[0]}")
    
    # 测试 2：查看 u_push 表结构（帮你排查为什么刚才删除会卡死）
    print("\n正在获取 u_push 表结构和索引信息...")
    cursor.execute("SHOW CREATE TABLE u_push;")
    create_stmt = cursor.fetchone()
    print("================== u_push 表结构 ==================")
    print(create_stmt[1])
    print("===================================================")
    
except Exception as e:
    print(f"❌ 数据库连接失败: {e}")
finally:
    if 'cursor' in locals():
        cursor.close()
    if 'conn' in locals() and conn.open:
        conn.close()
