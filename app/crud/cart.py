from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cart import Cart
from app.models.product import Product


# 获取购物车列表
async def get_cart_list(
    db: AsyncSession,
    user_id: int,
    skip: int = 0,
    limit: int = 100,
):
    stmt = (
        select(
            Cart.id,
            Cart.product_id,
            Cart.quantity,
            Cart.selected,
            Product.name,
            Product.cover,
            Product.price,
            Product.stock,
        )
        .join(Product, Cart.product_id == Product.id)
        .where(Cart.user_id == user_id)
        .order_by(Cart.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.all()


#按购物车的行id取记录，同时校验是不是这个用户的
async def get_cart_item_by_id(db: AsyncSession, user_id: int, cart_id: int) -> Cart | None:
    stmt = select(Cart).where(Cart.id == cart_id, Cart.user_id == user_id)
    res = await db.execute(stmt)
    return res.scalar_one_or_none()


#购物车中获取某一商品，返回orm对象
async def get_cart_item_by_user_product(db:AsyncSession,user_id:int,product_id:int)->Cart|None:
    stmt = select(Cart).where(Cart.user_id == user_id,Cart.product_id == product_id)
    res = await db.execute(stmt)
    return res.scalar_one_or_none()


#加入购物车
async def add_cart_item(db: AsyncSession,user_id:int,product_id:int,quantity:int=1) -> Cart:
    cart_item = await get_cart_item_by_user_product(db, user_id, product_id)
    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = Cart(user_id=user_id, product_id=product_id, quantity=quantity)
        db.add(cart_item)
    await db.flush()  
    return cart_item


#改数量/改勾选
async def update_cart_item(
    db: AsyncSession,
    cart_item: Cart,
    quantity: int | None = None,
    selected: bool | None = None,
) -> Cart:
    if quantity is not None:
        cart_item.quantity = quantity
    if selected is not None:
        cart_item.selected = selected
    await db.flush()
    return cart_item


#批量删除
async def remove_cart_items(db: AsyncSession, user_id: int, ids: list[int]) -> int:
    stmt = delete(Cart).where(Cart.user_id == user_id, Cart.id.in_(ids))
    result = await db.execute(stmt)
    return result.rowcount or 0


#清空购物车
async def clear_cart(db: AsyncSession, user_id: int) -> int:
    stmt = delete(Cart).where(Cart.user_id == user_id)
    result = await db.execute(stmt)
    return result.rowcount or 0
