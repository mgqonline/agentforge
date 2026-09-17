import os
import time
import pymysql
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def batch_delete_by_select_in():
    """
    【双段式精准狙击版】大表安全删除工具
    原理：先用只读 SELECT 查出符合条件的 ID 列表放入内存，然后通过 DELETE IN 批量删除。
    优点：强制走主键，0全表扫描，0间隙锁，彻底解决复杂条件下的卡死问题。
    """
    load_dotenv()
    
    # 请在这里填入你真实的数据库凭证
    db_host = os.getenv("DB_HOST", "127.0.0.1")
    db_port = int(os.getenv("DB_PORT", 3366))
    db_user = os.getenv("DB_USER", "root")
    db_pass = os.getenv("DB_PASS", "uther,_2020")
    db_name = os.getenv("DB_NAME", "uther_his")
    
    # ==========================================
    TARGET_TABLE = "u_push"
    PK_COLUMN = "id"
    
    START_ID = 1
    END_ID = 325622888
    CHUNK_SIZE = 30000
    SLEEP_TIME = 0.1
    
    # 记得把你要限制的 pushId 条件加进这里
    DELETE_CONDITION = " eventTime <= '2026-05-01 00:00:00' and eventType=3"
    # ==========================================
    
    logging.warning(f"⚠️ 即将对 `{TARGET_TABLE}` 执行【双段式精准】删除！步长: {CHUNK_SIZE}")
    confirm = input("确定继续吗？(yes/no): ")
    if confirm.lower() != 'yes':
        return

    try:
        conn = pymysql.connect(
            host=db_host, port=db_port, user=db_user, password=db_pass, database=db_name,
            charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor, autocommit=True
        )
        cursor = conn.cursor()
        
        if END_ID is None:
            cursor.execute(f"SELECT MAX({PK_COLUMN}) as max_id FROM {TARGET_TABLE}")
            row = cursor.fetchone()
            actual_end_id = row['max_id'] if row and row['max_id'] else START_ID
        else:
            actual_end_id = END_ID
            
        logging.info(f"✅ 最大 ID 确定为: {actual_end_id}。开始扫描...")
        
        total_deleted = 0
        current_id = START_ID
        
        PROGRESS_FILE = f"{TARGET_TABLE}_delete_progress.txt"
        if os.path.exists(PROGRESS_FILE):
            with open(PROGRESS_FILE, 'r') as f:
                saved_id = f.read().strip()
                if saved_id.isdigit():
                    if input(f"发现中断记录(pushId={saved_id})，是否继续？(yes/no): ").lower() == 'yes':
                        current_id = int(saved_id)
        
        # 1. 查找用的 SQL（只读）
        # 既然 PK_COLUMN 是真正的物理主键 id，MySQL 会完美走聚簇索引，不再需要 FORCE INDEX
        select_sql = f"""
            SELECT {PK_COLUMN} FROM {TARGET_TABLE} 
            WHERE {PK_COLUMN} >= %s AND {PK_COLUMN} < %s 
            AND {DELETE_CONDITION}
        """
        
        while current_id <= actual_end_id:
            next_id = current_id + CHUNK_SIZE
            try:
                # 【步骤 1】先查找符合条件的 ID
                cursor.execute(select_sql, (current_id, next_id))
                rows = cursor.fetchall()
                ids_to_delete = [str(r[PK_COLUMN]) for r in rows]
                
                # 【步骤 2】如果有需要删的数据，精确删除
                if ids_to_delete:
                    id_list_str = ",".join(ids_to_delete)
                    delete_sql = f"DELETE FROM {TARGET_TABLE} WHERE {PK_COLUMN} IN ({id_list_str})"
                    affected_rows = cursor.execute(delete_sql)
                    total_deleted += affected_rows
                    logging.info(f"[进度 {current_id}/{actual_end_id}] 命中并删除了 {affected_rows} 条数据。累计: {total_deleted}")
                else:
                    logging.info(f"[进度 {current_id}/{actual_end_id}] 无匹配数据，安全滑过。")
                
                current_id = next_id
                
                with open(PROGRESS_FILE, 'w') as f:
                    f.write(str(current_id))
                    
            except pymysql.MySQLError as e:
                logging.error(f"❌ 区间报错: {e}，休眠 5 秒重试...")
                time.sleep(5)
                continue
                
            time.sleep(SLEEP_TIME)
            
    except Exception as e:
        logging.error(f"异常退出: {e}")
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals() and conn.open: conn.close()

if __name__ == "__main__":
    batch_delete_by_select_in()
