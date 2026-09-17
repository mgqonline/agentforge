# SQLAlchemy 与 Alembic 企业级避坑指南

当你为你的 AI Agent 编写后台 API，或者搭建知识库持久化引擎时，**千万不要在生产环境使用轻量级的 `SQLite`**。一定要上 `MySQL` 或 `PostgreSQL`，并且全面拥抱 **SQLAlchemy 2.0 (Async 异步架构)**。

这里是一份你在企业中绝对会遇到的核心痛点解药清单。

---

## 1. 致命报错：`MissingGreenletError` (N+1 查询大考)

在旧的同步（Sync）时代，有一个极其隐蔽的性能杀手叫 **N+1 查询问题**：
你想查 100 个作家的文章。系统先发 1 条 SQL 查出 100 个作家，然后**在 for 循环里**又对每一个作家发起一条查询查他的文章（发了 100 条 SQL）。一条请求竟然打出了 101 条 SQL，数据库连接池瞬间爆炸。

在 SQLAlchemy 2.0 异步 (AsyncSession) 时代，它不惯着你这毛病了。
如果你不在最开始的 SQL 语句里把关联数据提前加载进来，你在代码下面尝试 `print(author.articles)` 时，它不会去偷偷发 SQL，而是会**当场引爆抛出 `MissingGreenletError` 让你崩溃报错**。

**终极解法（提前加载 Eager Loading）：**
1. **一对多 (One-to-Many)**：使用 `selectinload`。
   * 比如查 User 顺带查他下面的一堆 Articles。
   * 做法：`select(User).options(selectinload(User.articles))`
   * 原理：它会发两条单独的 SQL，用 `WHERE id IN (...)` 的方式极其优雅地把数据拉取到内存里拼装。
2. **多对一 (Many-to-One)**：使用 `joinedload`。
   * 比如查 Article 顺带把归属的 User 揪出来。
   * 做法：`select(Article).options(joinedload(Article.author))`
   * 原理：它会在底层生成极其硬核的 `LEFT OUTER JOIN` 语句，一板斧一条 SQL 连表查完所有数据。

---

## 2. 数据库连接池的神级参数：`pool_pre_ping=True`

**真实痛点**：公司的 MySQL 数据库设定了 8 小时闲置超时时间。如果你的 AI 服务半夜没人用，到了早上 9 点，第一批员工登录系统时，前十几个请求全部都会报一个极其著名的崩溃日志：
**`MySQL server has gone away` 或 `Lost connection to MySQL server`**。
因为你的 SQLAlchemy 连接池里缓存的是昨天的“死连接”！

**解决方案**：
在 `create_async_engine` 里面，一定要加上 `pool_pre_ping=True`！
开启后，每次你的接口尝试从池子里捞连接用时，SQLAlchemy 都会像雷达一样偷偷先发送一条 `SELECT 1` 的心跳信号测试一下这根网线断了没。如果断了，它会自动销毁这个死连接并立刻重新建一根新的，**这个过程对业务代码 100% 无感，从此彻底杜绝这种早起宕机事故。**

---

## 3. Alembic 数据库迁移 (DB Migration) 实战手册

你在本地写好了 Python Class Model 字段，怎么同步到线上的 MySQL 里去建表？
一旦上线后，如果产品经理要求你在表里新加一个 `is_vip` 字段，你难道要进数据库手写 `ALTER TABLE` 吗？
**绝对不要这么干！你必须使用 Alembic 来管控版本。**

### 企业级 Alembic 工作流：
1. **初始化环境**
   ```bash
   alembic init -t async alembic
   ```
   *注意：因为我们用的是 AsyncSession，必须加上 `-t async` 模板！*

2. **配置入口**
   打开 `alembic.ini`，配置你的 `sqlalchemy.url = postgresql+asyncpg://...`。
   打开 `alembic/env.py`，导入你定义的所有的 Model 和 Base：
   ```python
   from myapp.models import Base
   target_metadata = Base.metadata
   ```

3. **生成迁移脚本 (让它自动比对)**
   每当你修改了 Python 模型代码里的字段，在终端执行：
   ```bash
   alembic revision --autogenerate -m "add is_vip to users"
   ```
   Alembic 会极其聪明地比对线上的 MySQL 结构和你的 Python 代码，发现差异后，在 `versions` 文件夹下生成一个 Python 脚本，里面写好了升级和降级用的 `add_column` 函数。你可以打开这个脚本审查一下有没有问题。

4. **发版执行 (同步线上)**
   确认脚本没问题后，执行推向数据库：
   ```bash
   alembic upgrade head
   ```
   线上环境的 MySQL 会瞬间增加这个字段。不仅如此，Alembic 还会偷偷在线上建一张名为 `alembic_version` 的小表，用来记录当前的数据库版本号，绝不会重复建表报错。
