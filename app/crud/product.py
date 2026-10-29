"""
商品的数据库操作。

保留三个函数：
    get_product_list    列表（分类 + 关键词 + 排序 + 分页）
    get_product_count   同条件下的总数
    get_product_by_id   单个商品（详情）
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product

# 排序方式
#   default     最新上架（id 大的在前）
#   sales_desc  销量从高到低  ← 名字必须和路由的 Literal、前端传的值三处一致
#   price_asc   价格从低到高
#   price_desc  价格从高到低
SORTS = {
    "default": Product.id.desc(),
    "sales_desc": Product.sales.desc(),
    "price_asc": Product.price.asc(),
    "price_desc": Product.price.desc(),
}


async def get_product_list(
    db: AsyncSession,
    category_id: int | None = None,
    keyword: str | None = None,
    sort: str = "default",
    skip: int = 0,
    limit: int = 12,
) -> list[Product]:
    """
    取商品列表。

    category_id 传 None -> 全部分类（首页）
    keyword 传空        -> 不按名字筛
    """
    stmt = select(Product).where(Product.status == 1)

    if category_id is not None:
        stmt = stmt.where(Product.category_id == category_id)

    if keyword:
        # 模糊匹配商品名，% 代表任意字符
        stmt = stmt.where(Product.name.like(f"%{keyword}%"))

    stmt = stmt.order_by(SORTS.get(sort, SORTS["default"]))

    stmt = stmt.offset(skip).limit(limit)

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_product_count(
    db: AsyncSession,
    category_id: int | None = None,
    keyword: str | None = None,
) -> int:
    """
    同条件下的商品总数，用来算分页。
    """
    stmt = select(func.count(Product.id)).where(Product.status == 1)

    if category_id is not None:
        stmt = stmt.where(Product.category_id == category_id)

    if keyword:
        stmt = stmt.where(Product.name.like(f"%{keyword}%"))

    result = await db.execute(stmt)
    return result.scalar_one()


async def get_product_by_id(db: AsyncSession, product_id: int) -> Product | None:
    """按 ID 取单个商品（详情用）。"""
    result = await db.execute(select(Product).where(Product.id == product_id))
    return result.scalar_one_or_none()
