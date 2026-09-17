#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
u_atnd_intfatnd_his 历史数据批量删除脚本
- 按 intfatndid 区间分批删除，每批 20000 条
- 条件：cardtime <= '2025-08-01 00:00:00'
- 支持中断后断点续跑（进度保存在 checkpoint 文件中）
- 每批删除后休眠，避免对生产库造成压力
"""

import pymysql
import time
import json
import os
import logging
from datetime import datetime

# ========== 配置区 ==========
DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3366,
    "user": "root",
    "password": "uther,_2020",
    "database": "uther",
    "charset": "utf8mb4",
    "connect_timeout": 30,
    "read_timeout": 600,   # 大表全表扫描可能需要较长时间，调大至 600s
    "write_timeout": 300,
}

TABLE_NAME = "u_atnd_intfatnd_his"
CARD_TIME_LIMIT = "2025-08-01 00:00:00"   # 删除 cardtime <= 此值的数据
BATCH_SIZE = 20000                          # 每批处理条数
SLEEP_BETWEEN_BATCH = 0.5                  # 每批之间休眠秒数（可按负载调整）
CHECKPOINT_FILE = f"./checkpoint_{TABLE_NAME}.json"
LOG_FILE = f"./delete_{TABLE_NAME}.log"
# ============================

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


def load_checkpoint() -> dict:
    """加载断点进度"""
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r") as f:
            cp = json.load(f)
        log.info(f"恢复断点：last_deleted_id={cp['last_deleted_id']}，已删除总计={cp['total_deleted']}")
        return cp
    return {"last_deleted_id": 0, "total_deleted": 0}


def save_checkpoint(last_deleted_id: int, total_deleted: int):
    """保存断点进度"""
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(
            {
                "last_deleted_id": last_deleted_id,
                "total_deleted": total_deleted,
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            },
            f,
            ensure_ascii=False,
            indent=2,
        )


def get_connection():
    return pymysql.connect(**DB_CONFIG)


def get_id_range(conn) -> tuple[int, int]:
    """
    直接查全表 intfatndid 的 MIN/MAX（不带 cardtime 条件）。

    策略说明：
    - MIN/MAX 不加 WHERE，MySQL 直接读主键索引首尾叶节点，瞬间返回。
    - 删除时再用 cardtime 条件过滤，确保只删符合条件的行。
    - 这样做的代价是：区间扫描会覆盖全表 id 范围，
      但每批 DELETE 自带 cardtime 条件兜底，不会误删数据。
    """
    sql = f"SELECT MIN(intfatndid), MAX(intfatndid) FROM `{TABLE_NAME}`"
    log.info("正在查询全表 id 范围（走主键索引，极快）...")
    with conn.cursor() as cur:
        cur.execute(sql)
        row = cur.fetchone()
    return (row[0] or 0, row[1] or 0)


def delete_batch(conn, id_start: int, id_end: int) -> int:
    """
    删除 intfatndid 在 [id_start, id_end] 且 cardtime <= CARD_TIME_LIMIT 的数据
    返回实际删除行数
    """
    sql = f"""
        DELETE FROM `{TABLE_NAME}`
        WHERE intfatndid > %s
          AND intfatndid <= %s
          AND cardtime <= %s
        LIMIT {BATCH_SIZE}
    """
    with conn.cursor() as cur:
        affected = cur.execute(sql, (id_start, id_end, CARD_TIME_LIMIT))
        conn.commit()
    return affected


def run():
    log.info("=" * 60)
    log.info(f"开始删除任务：表={TABLE_NAME}，cardtime<={CARD_TIME_LIMIT}，batch={BATCH_SIZE}")

    cp = load_checkpoint()
    last_id = cp["last_deleted_id"]
    total_deleted = cp["total_deleted"]

    conn = get_connection()
    try:
        min_id, max_id = get_id_range(conn)
        if min_id == 0:
            log.info("没有符合条件的数据，任务结束。")
            return

        log.info(f"符合条件的 intfatndid 范围：[{min_id}, {max_id}]")

        # 如果断点 id 小于 min_id，从 min_id-1 开始（确保第一批能覆盖 min_id）
        if last_id < min_id - 1:
            last_id = min_id - 1
            log.info(f"断点 id 早于数据最小 id，调整起始 last_id={last_id}")

        batch_num = 0
        while last_id < max_id:
            batch_num += 1
            batch_end = min(last_id + BATCH_SIZE, max_id)

            try:
                affected = delete_batch(conn, last_id, batch_end)
            except pymysql.OperationalError as e:
                log.warning(f"数据库连接异常，尝试重连：{e}")
                try:
                    conn.close()
                except Exception:
                    pass
                time.sleep(3)
                conn = get_connection()
                affected = delete_batch(conn, last_id, batch_end)

            total_deleted += affected
            last_id = batch_end
            save_checkpoint(last_id, total_deleted)

            log.info(
                f"批次 #{batch_num:>6} | id区间 ({last_id - BATCH_SIZE:>12}, {batch_end:>12}] "
                f"| 本批删除 {affected:>6} 行 | 累计删除 {total_deleted:>10} 行"
            )

            if affected == 0:
                # 本区间无数据，直接跳过，不需要额外休眠
                continue

            time.sleep(SLEEP_BETWEEN_BATCH)

        log.info(f"任务完成！累计删除 {total_deleted} 行。")
        # 清除断点文件
        if os.path.exists(CHECKPOINT_FILE):
            os.remove(CHECKPOINT_FILE)
            log.info("断点文件已清除。")

    finally:
        conn.close()


if __name__ == "__main__":
    run()