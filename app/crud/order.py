"""
订单的数据库操作。

★ 关键：下单必须在一个事务里做完 ★
  - crud 只 flush，commit / rollback 由 get_db 负责
  - 所以这里任何一步抛 HTTPException，整个下单都会回滚（库存不会被扣错）

防止超卖靠两层：
  1. SELECT ... FOR UPDATE 把商品行锁住，别的事务排队
  2. UPDATE ... WHERE stock >= :qty 再兜一层，靠 rowcount 判断是否扣成功
"""

import random
from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cart import Cart
from app.models.order import Order, OrderItem
from app.models.product import Product


#生成业务单号：年月日时分秒 + 6 位随机数（20 位，不暴露自增 id）
def gen_order_no() -> str:
    return datetime.now().strftime("%Y%m%d%H%M%S") + f"{random.randint(0, 999999):06d}"


#按单号取订单（必须属于这个用户，防止看别人的订单）
async def get_order_by_no(db: AsyncSession, user_id: int, order_no: str) -> Order | None:
    return await db.scalar(
        select(Order).where(Order.order_no == order_no, Order.user_id == user_id)
    )


#取某个订单的明细
async def get_order_items(db: AsyncSession, order_id: int) -> list[OrderItem]:
    result = await db.execute(
        select(OrderItem).where(OrderItem.order_id == order_id).order_by(OrderItem.id)
    )
    return list(result.scalars().all())


#批量取明细（列表页用，避免 N+1 查询）
async def get_items_by_order_ids(db: AsyncSession, order_ids: list[int]) -> dict[int, list[OrderItem]]:
    if not order_ids:
        return {}
    result = await db.execute(
        select(OrderItem).where(OrderItem.order_id.in_(order_ids)).order_by(OrderItem.id)
    )
    grouped: dict[int, list[OrderItem]] = {}
    for item in result.scalars().all():
        grouped.setdefault(item.order_id, []).append(item)
    return grouped


#我的订单列表 + 总数
async def get_order_list(
    db: AsyncSession,
    user_id: int,
    status: str | None = None,
    page: int = 1,
    page_size: int = 10,
):
    conditions = [Order.user_id == user_id]
    if status:
        conditions.append(Order.status == status)

    total = await db.scalar(select(func.count(Order.id)).where(*conditions)) or 0

    result = await db.execute(
        select(Order)
        .where(*conditions)
        .order_by(Order.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().all()), total


#把「购物车行」或「直接购买的商品」统一成 [{'product_id','quantity','cart_id'}]
async def build_order_lines(
    db: AsyncSession,
    user_id: int,
    cart_item_ids: list[int] | None = None,
    items: list | None = None,
) -> list[dict]:
    #方式一：从购物车结算
    if cart_item_ids:
        result = await db.execute(
            select(Cart).where(Cart.user_id == user_id, Cart.id.in_(cart_item_ids))
        )
        carts = list(result.scalars().all())
        if len(carts) != len(set(cart_item_ids)):
            raise HTTPException(404, "购物车项不存在")
        lines = [
            {"product_id": c.product_id, "quantity": c.quantity, "cart_id": c.id}
            for c in carts
        ]
    #方式二：直接购买（同一个商品传了多次就合并数量）
    else:
        merged: dict[int, int] = {}
        for it in items or []:
            merged[it.product_id] = merged.get(it.product_id, 0) + it.quantity
        lines = [
            {"product_id": pid, "quantity": qty, "cart_id": None}
            for pid, qty in merged.items()
        ]

    if not lines:
        raise HTTPException(400, "没有要结算的商品")
    return lines


#创建订单（核心）
async def create_order(
    db: AsyncSession,
    user_id: int,
    receiver: dict,
    cart_item_ids: list[int] | None = None,
    items: list | None = None,
    remark: str | None = None,
) -> Order:
    # 1 整理出要下单的商品行
    lines = await build_order_lines(db, user_id, cart_item_ids, items)
    product_ids = [line["product_id"] for line in lines]

    # 2 ★ 行锁 ★ 把商品锁住，防止两个人同时下单把库存扣成负数
    result = await db.execute(
        select(Product).where(Product.id.in_(product_ids)).with_for_update()
    )
    products = {p.id: p for p in result.scalars().all()}

    # 3 校验：存在 / 上架 / 库存够，同时算出总额和明细快照
    total_amount = Decimal("0.00")
    snapshots = []

    for line in lines:
        product = products.get(line["product_id"])
        if product is None:
            raise HTTPException(400, "商品不存在或已下架")
        if product.status != 1:
            raise HTTPException(400, f"商品已下架：{product.name}")
        if product.stock < line["quantity"]:
            raise HTTPException(400, f"库存不足：{product.name} 仅剩 {product.stock} 件")

        subtotal = (product.price * line["quantity"]).quantize(Decimal("0.01"))
        total_amount += subtotal
        snapshots.append(
            {
                "product_id": product.id,
                "product_name": product.name,
                "product_cover": product.cover,
                "price": product.price,
                "quantity": line["quantity"],
                "subtotal": subtotal,
            }
        )

    # 4 写订单主表（无支付接口：下单即 paid，paid_at = 下单时间）
    now = datetime.now()
    order = Order(
        order_no=gen_order_no(),
        user_id=user_id,
        total_amount=total_amount,
        pay_amount=total_amount,
        status="paid",
        paid_at=now,
        remark=remark,
        **receiver,
    )
    db.add(order)
    await db.flush()

    # 5 写明细（全是快照）
    for snap in snapshots:
        db.add(OrderItem(order_id=order.id, **snap))

    # 6 扣库存：WHERE stock >= qty 是最后一道保险，rowcount 不是 1 就说明被别人抢了
    for line in lines:
        res = await db.execute(
            update(Product)
            .where(Product.id == line["product_id"], Product.stock >= line["quantity"])
            .values(
                stock=Product.stock - line["quantity"],
                sales=Product.sales + line["quantity"],
            )
        )
        if res.rowcount != 1:
            raise HTTPException(400, "库存不足，请刷新后重试")

    # 7 清掉这次结算的购物车行（立即购买的话没有购物车行，跳过）
    cart_ids = [line["cart_id"] for line in lines if line["cart_id"] is not None]
    if cart_ids:
        await db.execute(delete(Cart).where(Cart.user_id == user_id, Cart.id.in_(cart_ids)))

    await db.flush()
    return order


#取消订单：只允许 paid -> canceled，并把库存加回去
async def cancel_order(db: AsyncSession, user_id: int, order_no: str) -> Order:
    order = await get_order_by_no(db, user_id, order_no)
    if order is None:
        raise HTTPException(404, "订单不存在")
    if order.status != "paid":
        raise HTTPException(400, "当前状态不可取消")

    items = await get_order_items(db, order.id)

    for item in items:
        await db.execute(
            update(Product)
            .where(Product.id == item.product_id)
            .values(
                stock=Product.stock + item.quantity,
                # 用 greatest 兜底，避免历史数据异常导致 sales 变负数
                sales=func.greatest(Product.sales - item.quantity, 0),
            )
        )

    order.status = "canceled"
    order.canceled_at = datetime.now()
    await db.flush()
    return order
