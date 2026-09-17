from celery import Celery

# 初始化 Celery 实例
# broker: 任务队列（接收任务的信箱）。生产环境 99% 的公司使用 Redis。
# backend: 结果存储（存放生成完的研报/图片）。通常也用 Redis。
app = Celery(
    "ai_agent_tasks",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1",
    include=["tasks"] # 告诉 Celery 去哪个文件里寻找你定义的 @app.task
)

# 核心企业级配置
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    
    # 救命配置：防止大模型 API 限流时，一堆重试任务瞬间挤爆队列（并发风暴）
    # 强制限制针对 `generate_report` 这个任务，一分钟最多跑 10 个
    task_annotations={'tasks.generate_report': {'rate_limit': '10/m'}},
    
    # 防止大模型生成时间过长，卡死 Worker 进程（软超时警告，硬超时强杀）
    task_soft_time_limit=300, # 5分钟警告
    task_time_limit=360,      # 6分钟强杀
)

# 定时任务配置 (Celery Beat)
# 真实场景：每天半夜去爬取各个业务系统的新文档，灌入向量库（RAG 知识更新）
app.conf.beat_schedule = {
    'sync-knowledge-base-every-midnight': {
        'task': 'tasks.sync_vector_db',
        'schedule': 86400.0, # 每天执行一次 (或者使用 crontab 表达式)
    },
}
