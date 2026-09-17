# 企业级 AI Agent 的 Celery 分布式调度指南

之前在讲 FastAPI 时，我们提到了 `BackgroundTasks`。既然 FastAPI 自带了后台任务，为什么阿里、腾讯乃至国外的巨头在做 AI 系统时，还要引入沉重的 Celery + Redis？

## 1. 为什么不用 FastAPI 的 `BackgroundTasks`？
* **重启就丢数据**：`BackgroundTasks` 是存在于当前 Python 进程的**内存**里的。如果这台服务器突然宕机或者发版重启，里面排队排到一半的“大模型生成任务”全丢了，用户会把你骂死。Celery 把任务序列化存进了 **Redis 硬盘**，死机重启后接着跑。
* **算力无法分布式负载均衡**：如果你只有一个服务器，接了 100 个人同时生成图片的请求，这台服务器的 GPU 会当场融化。Celery 允许你部署 **10 台**专门插着高端显卡的服务器（Worker），它们一起连向一个公共的 Redis 去抢任务干。这是**实现 AI 算力集群化**的唯一解法！

---

## 2. Agent 中最经典的四大应用场景 (结合代码)

### 场景一：LLM 接口的“防抖与续命” (指数退避算法)
大模型的 API 是极其脆弱的，不仅常常报 429 频率超限，甚至有时会莫名其妙中断。
* **绝招**：在 `@app.task(bind=True, max_retries=3)` 中，我们利用 `raise self.retry(countdown=2 ** retries)` 实现了**指数退避算法**。如果报错了，第一次等 1 秒再试，第二次等 2 秒，第三次等 4 秒。这极大缓解了第三方 API 的瞬间并发风暴。

### 场景二：Map-Reduce 分布式 Agent 协作 (Chord)
比如老板让你写一份《手机行业竞品分析》。
* 传统 Agent：先去搜小米，花 10 秒；再搜华为，花 10 秒；最后写报告花 10 秒。总耗时 30 秒。
* **Celery Chord 绝招**：我们派发 3 个并行的 `subagent_research` 任务。如果是分布式集群，这就相当于有 3 台服务器同时去搜！最后自动通过 `chord` 原语汇总到 `mainagent_summarize` 撰写报告。总耗时压缩到了极致的 **10+10=20秒**。

### 场景三：防大模型无限死循环卡死机器 (软硬超时机制)
如果 Agent 写代码陷入了死循环，或者因为没有 `<EOS>` Token 一直在废话连篇，会永远霸占着一块极其昂贵的 GPU 显卡。
* **配置绝招**：在 `celery_app.py` 中配置 `task_time_limit=360`。只要生成时间超过 6 分钟，Celery 框架会在操作系统底层发出 `SIGKILL` 强制将这个恶灵进程杀掉，释放显卡资源救活系统！

### 场景四：企业级知识库每日定时更新 (Celery Beat)
* **业务痛点**：公司的规章制度或者商品价格每天都在变，如果不把最新的文档灌入 FAISS，RAG 的回答就会过时导致客诉。
* **配置绝招**：配置 `beat_schedule`。开启一个 Celery Beat 进程，它就是一个基于 Redis 的永不宕机的神级 Cronjob 系统，每天半夜 12 点准时拉起切分和向量化脚本，自动维持知识库新鲜度。

---

## 3. 本地测试与运行命令

要真正在本地跑起来这套代码，你需要开启三个终端：

1. **终端 1：启动 Redis 容器（必须有）**
   ```bash
   docker run -d -p 6379:6379 redis
   ```
2. **终端 2：启动干活的 Celery Worker**
   ```bash
   # 进入目录执行
   celery -A celery_app worker --loglevel=info
   ```
3. **终端 3：用 Python 模拟抛出任务给 Redis**
   ```bash
   python tasks.py
   ```
   *你会瞬间看到终端 3 打印“任务已投递”，而终端 2 的 Worker 会开始咔咔干活！*
