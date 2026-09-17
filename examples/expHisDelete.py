import pymysql
import time
import logging
import os
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler('delete_null_cardtime.log'),
        logging.StreamHandler()
    ]
)

DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3366,
    'user': 'root',
    'password': 'uther,_2020',
    'database': 'uther',
    'charset': 'utf8mb4',
}

BATCH_SIZE = 50000
SLEEP_SECONDS = 0.5
CHECKPOINT_FILE = 'delete_checkpoint.json'


def save_checkpoint(batch_start, total_deleted):
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump({'batch_start': batch_start, 'total_deleted': total_deleted}, f)


def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, 'r') as f:
            data = json.load(f)
            logging.info(f"发现断点文件，从 expid={data['batch_start']} 继续，已删除 {data['total_deleted']} 条")
            return data['batch_start'], data['total_deleted']
    return None, 0


def clear_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)
        logging.info(f"断点文件已清除: {CHECKPOINT_FILE}")


def get_min_max_expid_fast(conn):
    """
    走主键索引，极速获取全表 min/max，不加 WHERE 条件
    InnoDB 主键 B+Tree 首尾节点，毫秒级返回
    """
    with conn.cursor() as cur:
        cur.execute("SELECT MIN(expid), MAX(expid) FROM u_atnd_std_expdetail_his")
        return cur.fetchone()


def delete_batch(conn, min_id, max_id):
    with conn.cursor() as cur:
        cur.execute("""
            DELETE FROM u_atnd_std_expdetail_his
            WHERE expid BETWEEN %s AND %s
              AND cardtime IS NULL
        """, (min_id, max_id))
        affected = cur.rowcount
        conn.commit()
        return affected


def main():
    conn = pymysql.connect(**DB_CONFIG)
    logging.info("数据库连接成功")

    try:
        batch_start, total_deleted = load_checkpoint()

        if batch_start is None:
            # 不带 WHERE 查 min/max，走主键索引，极快
            min_expid, max_expid = get_min_max_expid_fast(conn)
            if min_expid is None:
                logging.info("表为空，退出")
                return
            batch_start = min_expid
            logging.info(f"全新开始，expid 范围: {min_expid} ~ {max_expid}")
            save_checkpoint(batch_start, 0)
        else:
            # 断点恢复，同样不带 WHERE 查 max
            _, max_expid = get_min_max_expid_fast(conn)
            logging.info(f"断点恢复，max_expid={max_expid}")

        while batch_start <= max_expid:
            batch_end = batch_start + BATCH_SIZE - 1

            affected = delete_batch(conn, batch_start, batch_end)
            total_deleted += affected

            next_start = batch_start + BATCH_SIZE
            save_checkpoint(next_start, total_deleted)

            if affected > 0:
                logging.info(
                    f"删除 expid [{batch_start} ~ {batch_end}]，"
                    f"本批删除 {affected} 条，累计 {total_deleted} 条"
                )
            else:
                # 该区间无 null 数据，静默跳过，每100批打一次进度
                if (batch_start // BATCH_SIZE) % 100 == 0:
                    logging.info(
                        f"扫描进度 expid={batch_start}，累计删除 {total_deleted} 条"
                    )

            batch_start += BATCH_SIZE
            time.sleep(SLEEP_SECONDS)

        logging.info(f"全部完成，共删除 {total_deleted} 条")
        clear_checkpoint()

    except KeyboardInterrupt:
        logging.info(f"手动中断，断点已保存至 {CHECKPOINT_FILE}")

    except Exception as e:
        logging.error(f"异常退出: {e}")
        raise

    finally:
        conn.close()


if __name__ == '__main__':
    main()