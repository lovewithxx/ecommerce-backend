"""
数据库：异步引擎 + 会话工厂 + get_db。

三个对象：
    async_engine       连接池，整个应用只有一个
    AsyncSessionLocal  会话工厂，每个请求建一个
    get_db()           依赖函数，FastAPI 靠 Depends(get_db) 注入

★ 本项目的约定：crud 只 flush 不 commit ★
    接口正常执行完 -> get_db 统一 commit
    接口抛异常     -> get_db 统一 rollback
这样"建用户 + 发 token"这种多步操作才是原子的。
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config.app_conf import settings

async_engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,      # 打印 SQL，调试用；上线改成 False
    pool_size=10,             # 常驻连接
    max_overflow=20,          # 高峰期最多再开 20 个
    pool_pre_ping=True,       # 取连接前先探活，防止 MySQL 8 小时断连
    pool_recycle=3600,        # 一小时回收
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db():
    """请求级数据库会话。用法：db: AsyncSession = Depends(get_db)"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
