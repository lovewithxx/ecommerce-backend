"""
建表脚本（开发用）。

运行：
    .\.venv\Scripts\python.exe -m tools.init_db

它做两件事：
    1. 按 ORM 模型建表（已存在的表不会动，不会删数据）
    2. 打印建完之后库里有哪些表

=====================================================================
【为什么用 create_all 而不是 Alembic 迁移】
=====================================================================
Alembic 是生产级方案，能把表结构变更写成版本脚本、可回滚。
但现阶段引入它只会增加理解负担。

现在的约定：
    学习阶段用 create_all（改字段就手动 DROP TABLE 重来）
    上线前再引入 Alembic

=====================================================================
【★ create_all 只建"已经 import 过"的模型 ★】
=====================================================================
create_all 遍历的是 Base.metadata 里登记的表。
而表是在 model 文件【被 import 时】才登记进去的。

所以本文件必须 import 所有 model 模块 —— 哪怕没直接用到。
下面那行 `import app.models.users  # noqa: F401` 看着多余，删了就会：
    create_all 什么都不建，而且不报错
这是很多人第一次用 SQLAlchemy 时最迷惑的地方。
=====================================================================
"""

import asyncio
import sys
from pathlib import Path

# 允许从任意目录运行：把项目根加入 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text                                    # noqa: E402

import app.models.users                                        # noqa: F401, E402  ★ 必须导入，否则表不登记
import app.models.product                                      # noqa: F401, E402  ★ 同理：category / product
from app.config.app_conf import settings                       # noqa: E402
from app.config.db_conf import async_engine                    # noqa: E402
from app.models.base import Base                               # noqa: E402


async def main() -> None:
    print(f"目标数据库：{settings.db_name}@{settings.db_host}:{settings.db_port}")

    async with async_engine.begin() as conn:
        # run_sync：把同步的 create_all 放到异步连接上执行
        await conn.run_sync(Base.metadata.create_all)

    # 建完再查一遍，确认真的进库了
    async with async_engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT TABLE_NAME, TABLE_COMMENT FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = :db ORDER BY TABLE_NAME"
            ),
            {"db": settings.db_name},
        )
        rows = list(result)

    print(f"\n建表完成，库中共 {len(rows)} 张表：")
    for name, comment in rows:
        print(f"  - {name:<20} {comment or ''}")

    await async_engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
