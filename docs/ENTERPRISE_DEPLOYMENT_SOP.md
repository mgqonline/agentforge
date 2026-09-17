# 🏢 AgentForge · 企业私有化部署与高可用运维手册 (SOP)

> **文档性质**：生产环境部署指引、运维应急响应与硬件容量规划手册  
> **面向对象**：甲方技术主管、DevOps 运维工程师、系统实施顾问

---

## 一、 生产环境硬件容量规划与选型指南

在企业私有化内网部署大模型与 AgentForge 全栈系统时，推荐根据业务规模与模型参数进行如下硬件选型：

| 业务场景 | 推荐模型规模型号 | 最低显存要求 (GPU VRAM) | 最低系统内存 (RAM) | 最低磁盘与存储 (SSD) | 推荐服务器硬件配置 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **轻量企业知识库** | Qwen2.5-7B-Instruct (INT4) | **8 GB** (RTX 4060 / Mac M2) | 16 GB | 100 GB NVMe | 1 台单卡轻量 GPU 服务器 |
| **标准智能体生产** | DeepSeek-R1-Distill-14B (AWQ) | **16 GB** (RTX 4080 / T4 x 2) | 32 GB | 250 GB NVMe | 1 台 24G 显存 (如 RTX 3090/4090) |
| **复杂逻辑与研报** | Qwen2.5-32B / DeepSeek-32B | **32 GB - 48 GB** (A10 / A6000) | 64 GB | 500 GB NVMe | 2 张 24G GPU 或 1 张 A100-40G |
| **集团级中枢大底座**| DeepSeek-V3 / 70B 专家混合模型 | **80 GB x 2 - 4** (A100/H800 集群) | 128 GB+ | 1 TB NVMe | 4 卡并行分布式 GPU 算力集群 |

### 💡 生产显存容量估算速算法则
$$\text{总显存需求 (GB)} = (\text{模型参数量 (B)} \times \text{精度字节数}) + \text{KV Cache 显存} + \text{系统预留 (约 2GB)}$$
* *以 FP16 (2字节/参数) 计算，14B 模型静态显存需 28GB；经 AWQ/INT4 量化后，静态显存压缩至仅需 8~10GB。*

---

## 二、 生产服务标准部署步骤 (Docker 一键编排)

### 1. 生产环境配置初始化
```bash
# 1. 克隆生产代码库
git clone https://github.com/your-org/agentforge.git
cd agentforge

# 2. 从模板生成生产环境变量配置文件
cp .env.example .env

# 3. 编辑生产关键参数 (关闭 DEBUG，配置强密码)
vim .env
```

生产必配关键参数说明：
```ini
POSTGRES_USER=agentforge_prod_user
POSTGRES_PASSWORD=SetAStrongPassword_2026!
POSTGRES_DB=agentforge_prod_db
JWT_SECRET_KEY=YourSuperSecretProductionJWTKeyMinimum32Chars
OPENAI_API_BASE=https://your-internal-llm-gateway/v1
OPENAI_API_KEY=sk-internal-token
```

### 2. 一键启动生产集群
```bash
# 启动包含 PostgreSQL、Redis、FastAPI 网关、Celery Worker 和前端 React 终端的全套生产集群
docker-compose -f docker-compose.prod.yml up -d

# 检查服务健康状态 (全部为 healthy 即为就绪)
docker-compose -f docker-compose.prod.yml ps
```

---

## 三、 冷启动预热与健康巡检 SOP

由于大模型嵌入矩阵（如 BGE-M3）首次载入显存需要 10~20 秒，系统提供了确定性的预热健康巡检接口：

```bash
# 1. 探测 API 网关探活接口
curl -f http://127.0.0.1:8000/docs || echo "服务尚未就绪"

# 2. 触发一次微小向量预热请求
curl -X POST http://127.0.0.1:8000/api/warmup \
  -H "Authorization: Bearer <YourAdminToken>"

# 3. 检查 Celery 异步计算节点状态
docker exec -it agentforge_celery_worker celery -A 14-celery-advanced.celery_app status
```

---

## 四、 数据库备份、灾难恢复与运维应急

### 1. PostgreSQL 每日定时备份脚本 (Crontab)
创建备份脚本 `/opt/backup_pg.sh`：
```bash
#!/bin/bash
BACKUP_DIR="/data/backups/agentforge_pg"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

docker exec agentforge_postgres pg_dump -U agentforge_prod_user agentforge_prod_db \
  | gzip > "$BACKUP_DIR/backup_$DATE.sql.gz"

# 仅保留最近 30 天备份
find $BACKUP_DIR -type f -name "*.sql.gz" -mtime +30 -delete
```

### 2. 灾难恢复导入流程
```bash
# 解压并回灌数据
gunzip < /data/backups/agentforge_pg/backup_20260916.sql.gz | \
  docker exec -i agentforge_postgres psql -U agentforge_prod_user -d agentforge_prod_db
```

### 3. Redis 队列积压应急排查
当监控告警提示任务排队过多时：
```bash
# 查询当前 Celery 队列堆积任务数量
docker exec -it agentforge_redis redis-cli -a "<密码>" LLEN celery

# 临时横向扩容 Celery Worker 容器实例
docker-compose -f docker-compose.prod.yml up -d --scale celery_worker=4
```
