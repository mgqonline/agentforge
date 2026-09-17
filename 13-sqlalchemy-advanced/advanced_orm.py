import asyncio
from typing import List
from sqlalchemy import String, Integer, ForeignKey, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, selectinload, joinedload
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# =====================================================================
# 一、 引擎与连接池高阶配置 (pool_size / pool_pre_ping)
# =====================================================================
DATABASE_URL = "sqlite+aiosqlite:///./test_ai_agent.db"
# 在企业级生产环境中，你极大概率面对的是 MySQL 或 PostgreSQL：
# DATABASE_URL = "postgresql+asyncpg://user:pwd@127.0.0.1/dbname"

engine = create_async_engine(
    DATABASE_URL, 
    echo=False, # 设为 True 可以在终端打印出底层自动生成的 SQL 语句，排查 N+1 时必备！
    
    # 【连接池核心三剑客】(注意：SQLite 是单文件数据库，不生效以下连接池，但在 MySQL/PG 中必须配)
    # pool_size=10,          # 常驻连接池大小。哪怕没请求，也保持 10 个 TCP 连接不断开。
    # max_overflow=20,       # 并发顶峰时，允许额外再建立 20 个连接。总并发上限 30。
    # pool_pre_ping=True     # 🌟 救命参数！每次从池子里取连接前，先发一个 SELECT 1 测试连接是否存活。
                             # 完美解决恶心的 "MySQL server has gone away" 断链报错！
)

# 生成极其强大的 AsyncSession 工厂
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

class Base(DeclarativeBase):
    pass

# =====================================================================
# 二、 关联与双向绑定 (relationship + back_populates)
# =====================================================================
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    
    # 1对多：一个用户可以有多篇文章。
    # back_populates="author" 代表去 Article 类里找一个叫 author 的属性，让它们建立血脉相连的双向绑定。
    # cascade 意味着如果删除了 User，他名下的 Article 也会被级联无情抹杀。
    articles: Mapped[List["Article"]] = relationship(
        "Article", back_populates="author", cascade="all, delete-orphan"
    )

class Article(Base):
    __tablename__ = "articles"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    
    # 多对1：多篇文章归属一个用户。
    author: Mapped["User"] = relationship("User", back_populates="articles")

# 初始化塞点测试数据
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        
    async with AsyncSessionLocal() as session:
        u1 = User(name="AI_初级研究员")
        # 直接给 list 赋值，SQLAlchemy 底层会自动提取 id 并写入 Article.user_id 字段
        u1.articles = [Article(title="Agent 理论基础"), Article(title="SQLAlchemy 进阶坑位")]
        session.add(u1)
        await session.commit()

# =====================================================================
# 三、 彻底消灭 N+1 问题 (selectinload / joinedload)
# =====================================================================
async def test_n_plus_one_solver():
    async with AsyncSessionLocal() as session:
        
        # 🚨 【灾难级写法 (N+1)】
        # 如果你只写 `select(User)`，然后在下面 for 循环里去点 `user.articles`，
        # 在传统的同步代码中，数据库会被疯狂轮询 N 次（用户越多，查的次数越多）。
        # 在 2.0 异步 (Async) 代码中，因为无法在事件循环里隐式发起 I/O 请求，
        # 直接点 `user.articles` 会当场引发恐怖的崩溃报错：【MissingGreenletError】！

        # 👑 【王者写法 (selectinload / joinedload)】
        # options(selectinload(User.articles)) 会提前一次性把所有文章加载进内存。
        # 底层其实只发了两条极速 SQL：
        # 1. SELECT * FROM users
        # 2. SELECT * FROM articles WHERE user_id IN (查出来的所有 UserID)
        stmt = select(User).options(selectinload(User.articles))
        
        result = await session.execute(stmt)
        # 用 scalars() 解包取出真实对象
        users = result.scalars().all()
        
        print("\n=== 数据提取结果 ===")
        for user in users:
            print(f"用户: {user.name}")
            # 因为之前加了 selectinload 提前装载，这里的循环提取极度丝滑，0 报错，0 延迟！
            for article in user.articles:
                print(f"  └─ 撰写了研报: 《{article.title}》")
        print("\n✅ 测试完毕。因为使用了 selectinload，没有触发 MissingGreenletError。")

async def main():
    await init_db()
    await test_n_plus_one_solver()

if __name__ == "__main__":
    asyncio.run(main())
