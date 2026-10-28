from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Category, Product

#获取商品分类列表
async def get_category_list(db: AsyncSession,skip: int = 0,limit: int = 100,) -> list[Category]:
    stmt = (select(Category).where(Category.status == 1).order_by(Category.sort.asc()).offset(skip).limit(limit))
    result = await db.execute(stmt)
    return list(result.scalars().all())





#读取某一分类商品数量
async def get_product_count_by_category(db: AsyncSession, category_id: int) -> int:
    stmt = select(func.count(Product.id)).where(
        Product.category_id == category_id,
        Product.status == 1,
    )
    result = await db.execute(stmt)
    return result.scalar_one()
