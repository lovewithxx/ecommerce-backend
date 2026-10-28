from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product

# 排序方式 -> ORDER BY 子句
# default 按销量（首页通常按热度），newest 按 id 倒序（近似上架时间）
SORTS = {
    "default": Product.sales.desc(),
    "sales": Product.sales.desc(),
    "price_asc": Product.price.asc(),
    "price_desc": Product.price.desc(),
    "newest": Product.id.desc(),
}


def _build_query(category_id: int | None, keyword: str | None) -> Select:
    """
    把筛选条件拼成一个查询。
    """
    stmt = select(Product).where(Product.status == 1)

    if category_id is not None:
        stmt = stmt.where(Product.category_id == category_id)

    if keyword:
        stmt = stmt.where(Product.name.like(f"%{keyword}%"))

    return stmt


async def get_product_list(
    db: AsyncSession,
    category_id: int | None = None,
    keyword: str | None = None,
    sort: str = "default",
    skip: int = 0,
    limit: int = 20,
) -> list[Product]:
    """按条件取商品，带排序和分页。"""
    stmt = _build_query(category_id, keyword)
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
    同条件下的商品总数（用来算分页的 hasMore）。

    ★ 筛选条件必须和 get_product_list 完全一致 ★
        否则会出现"列表返回 3 条、总数却是 400"，分页直接算错。
        所以两边都用 _build_query 拼条件，只差 order_by / offset / limit。
    """
    stmt = _build_query(category_id, keyword)
    count_stmt = select(func.count()).select_from(stmt.subquery())

    result = await db.execute(count_stmt)
    return result.scalar_one()


async def get_product_by_id(db: AsyncSession, product_id: int) -> Product | None:
    """按 ID 取单个商品（详情用）。"""
    result = await db.execute(select(Product).where(Product.id == product_id))
    return result.scalar_one_or_none()
