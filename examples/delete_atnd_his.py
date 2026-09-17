import os
import time
import pymysql
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def batch_delete_atnd_his():
    """
    考勤历史明细表 (u_atnd_atnddetail_his) 专属安全清理脚本
    架构：双段式精准狙击 (防 Secondary Index 走错、防锁表)
    """
    load_dotenv()
    
    # 数据库配置
    db_host = os.getenv("DB_HOST", "127.0.0.1")
    db_port = int(os.getenv("DB_PORT", 3366))
    db_user = os.getenv("DB_USER", "root")
    db_pass = os.getenv("DB_PASS", "uther,_2020")
    db_name = os.getenv("DB_NAME", "uther")
    
    # ==========================================
    TARGET_TABLE = "u_atnd_atnddetail_his"
    
    # 你的主键是复合主键 (atndid, cardtime)，但由于 atndid 是最左前缀，
    # 我们可以完全依靠 atndid 来作为滑动游标。
    PK_PREFIX = "atndid"
    
    # 请填入表中的最小 atndid（可以先在 DB 里查一下 SELECT MIN(atndid) FROM...）
    START_ID = 2146489491
    END_ID = 2290595371  # 自动查最大
    CHUNK_SIZE = 50000
    SLEEP_TIME = 0.1
    
    # 目标删除时间
    TARGET_DATE = "2025-08-01 00:00:00"
    # ==========================================
    
    logging.warning(f"⚠️ 即将对 `{TARGET_TABLE}` 执行大表分段删除！步长: {CHUNK_SIZE}")
    logging.warning(f"删除目标：cardtime < '{TARGET_DATE}' 的历史数据")
    confirm = input("确定继续吗？(yes/no): ")
    if confirm.lower() != 'yes':
        return

    try:
        conn = pymysql.connect(
            host=db_host, port=db_port, user=db_user, password=db_pass, database=db_name,
            charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor, autocommit=True
        )
        cursor = conn.cursor()
        
        # 探测全表最大 atndid
        if END_ID is None:
            logging.info(f"正在查询最大 {PK_PREFIX}...")
            cursor.execute(f"SELECT MAX({PK_PREFIX}) as max_id FROM {TARGET_TABLE}")
            row = cursor.fetchone()
            actual_end_id = row['max_id'] if row and row['max_id'] else START_ID
        else:
            actual_end_id = END_ID
            
        logging.info(f"✅ 最大 {PK_PREFIX} 确定为: {actual_end_id}。开始扫描...")
        
        total_deleted = 0
        current_id = START_ID
        
        # 断点续传文件
        PROGRESS_FILE = f"{TARGET_TABLE}_delete_progress.txt"
        if os.path.exists(PROGRESS_FILE):
            with open(PROGRESS_FILE, 'r') as f:
                saved_id = f.read().strip()
                if saved_id.isdigit():
                    if input(f"发现中断记录(atndid={saved_id})，是否继续？(yes/no): ").lower() == 'yes':
                        current_id = int(saved_id)
        
        # ==============================================================
        # 核心 SQL 构造：直接使用 BETWEEN 区间进行删除
        # 因为 atndid 是复合主键的第一个字段，MySQL 会完美地走聚簇索引的范围扫描，
        # 直接在这里带上 cardtime 的条件，无需再多做一次 SELECT 内存转换，性能最高。
        # ==============================================================
        delete_sql = f"""
            DELETE FROM {TARGET_TABLE} 
            WHERE atndid BETWEEN %s AND %s 
            AND (cardtime < '{TARGET_DATE}' OR recdtime < '{TARGET_DATE}')
        """
        
        while current_id <= actual_end_id:
            # 使用 BETWEEN 时，是闭区间 [current_id, next_id_boundary]
            next_id_boundary = current_id + CHUNK_SIZE - 1
            
            try:
                # 打印真实执行的 SQL (pymysql 提供的 mogrify 方法能准确拼装参数)
                actual_sql = cursor.mogrify(delete_sql, (current_id, next_id_boundary))
                # logging.info(f"👉 [即将执行 SQL] {actual_sql.strip()}")
                
                # 直接执行区间删除
                affected_rows = cursor.execute(delete_sql, (current_id, next_id_boundary))
                total_deleted += affected_rows
                
                logging.info(f"[进度 {current_id}/{actual_end_id}] 区间 [{current_id}, {next_id_boundary}] 删除了 {affected_rows} 条数据。累计: {total_deleted}")
                
                # 滑块推进到下一个区间的起点
                current_id = next_id_boundary + 1
                
                # 持久化当前进度
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
        logging.info("连接关闭。")

if __name__ == "__main__":
    batch_delete_atnd_his()
