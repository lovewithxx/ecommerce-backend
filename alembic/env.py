"""
Alembic 迁移环境配置。

  1. target_metadata 必须指向 Base.metadata，并且**所有 model 都要 import 进来。
     少 import 一张表，autogenerate 就会以为这张表「不该存在」，
     生成一条 DROP TABLE —— 这是 Alembic 最经典的翻车现场。
  2. 连接串从项目配置读（app.config.app_conf.settings），不写死在 alembic.ini 里，
     免得密码进版本库。想临时跑别的库，用环境变量 ALEMBIC_DATABASE_URL 覆盖。
"""

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.config.app_conf import settings
from app.models.base import Base

# ---------- ★ 全部 model 必须 import，少一个都会被误判成「该删表」★ ----------
import app.models.users  # noqa: F401  user / user_token
import app.models.product  # noqa: F401  category / product
import app.models.favorite  # noqa: F401
import app.models.cart  # noqa: F401
import app.models.address  # noqa: F401
import app.models.order  # noqa: F401  order / order_item

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# autogenerate 靠这个对象和数据库做对比
target_metadata = Base.metadata

# 连接串优先级：环境变量 > .env 里的配置
# 想在测试库上试迁移，不用改任何文件：
#   $env:ALEMBIC_DATABASE_URL="mysql+aiomysql://root:pwd@127.0.0.1:3306/other_db?charset=utf8mb4"
db_url = os.getenv("ALEMBIC_DATABASE_URL") or settings.database_url
config.set_main_option("sqlalchemy.url", db_url)


def run_migrations_offline() -> None:
    """
    离线模式：不连数据库，只把 SQL 打出来。
    用法：alembic upgrade head --sql
    """
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # 字段类型改了（varchar(50) -> varchar(100)）也能检测出来
        compare_type=True,
        # 字段默认值变化也检测
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
