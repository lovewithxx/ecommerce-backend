from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.favorite import Favorite
from app.models.product import Product

#某用户是否收藏这个商品
async def is_favored(db: AsyncSession, user_id: int, product_id: int) -> bool:
    stmt = select(Favorite.id).where(
        Favorite.user_id == user_id,
        Favorite.product_id == product_id,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


#添加收藏
async def add_favorite(db: AsyncSession, user_id: int, product_id: int) -> bool:
  
    if await is_favored(db, user_id, product_id):
        return False

    db.add(Favorite(user_id=user_id, product_id=product_id))
    await db.flush()
    return True

#取消收藏
async def remove_favorite(db: AsyncSession, user_id: int, product_id: int) -> bool:

    stmt = delete(Favorite).where(
        Favorite.user_id == user_id,
        Favorite.product_id == product_id,
    )
    result = await db.execute(stmt)
    await db.flush()
    return (result.rowcount or 0) > 0


#获取收藏列表
async def get_favorite_list(db: AsyncSession, user_id: int):
   
    stmt = (
        select(Product, Favorite.created_at)
        .join(Favorite, Favorite.product_id == Product.id)
        .where(
            Favorite.user_id == user_id,
            Product.status == 1,
        )
        .order_by(Favorite.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.all())
