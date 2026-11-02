import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.db_conf import get_db
from app.crud.address import get_address
from app.crud.order import (
    cancel_order,
    create_order,
    get_items_by_order_ids,
    get_order_by_no,
    get_order_items,
    get_order_list,
)
from app.models.order import Order, OrderItem
from app.models.users import User
from app.schemas.order import (
    STATUS_TEXT,
    OrderCancelSchema,
    OrderCreateOut,
    OrderCreateSchema,
    OrderDetailOut,
    OrderItemOut,
    OrderListOut,
)
from app.untils.auth import get_current_user
from app.untils.response import page_response, success_response

logger = logging.getLogger("ec_platform")

router = APIRouter(prefix="/api/order", tags=["订单"])


#明细 ORM -> 出参
def item_to_out(item: OrderItem) -> OrderItemOut:
    return OrderItemOut(
        product_id=item.product_id,
        product_name=item.product_name,
        product_cover=item.product_cover,
        price=float(item.price),
        quantity=item.quantity,
        subtotal=float(item.subtotal),
    )


#订单 ORM -> 列表出参（items 只带前 3 条）
def order_to_list_out(order: Order, items: list[OrderItem]) -> OrderListOut:
    return OrderListOut(
        order_no=order.order_no,
        pay_amount=float(order.pay_amount),
        status=order.status,
        status_text=STATUS_TEXT.get(order.status, order.status),
        created_at=order.created_at,
        item_count=len(items),
        items=[item_to_out(i) for i in items[:3]],
    )


@router.post("/create", description="创建订单（购物车结算 / 立即购买）")
async def req_create_order(
    body: OrderCreateSchema,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    下单。整个过程在一个事务里：
        行锁锁商品 -> 校验库存 -> 写订单 -> 写明细 -> 扣库存 -> 清购物车
    任何一步失败都会回滚，不会出现"扣了库存却没生成订单"。
    """
    #收货信息：优先用地址簿里的（快照进订单，不是存 address_id）
    if body.address_id is not None:
        addr = await get_address(db, current.id, body.address_id)
        if addr is None:
            raise HTTPException(404, "收货地址不存在")
        receiver = {
            "receiver_name": addr.receiver_name,
            "receiver_phone": addr.receiver_phone,
            "receiver_address": f"{addr.province}{addr.city}{addr.district}{addr.detail}",
        }
    else:
        receiver = {
            "receiver_name": body.receiver_name,
            "receiver_phone": body.receiver_phone,
            "receiver_address": body.receiver_address,
        }

    order = await create_order(
        db,
        user_id=current.id,
        receiver=receiver,
        cart_item_ids=body.cart_item_ids,
        items=body.items,
        remark=body.remark,
    )

    logger.info(
        "用户 %s 下单成功 order_no=%s 金额=%s", current.username, order.order_no, order.pay_amount
    )

    return success_response(
        message="下单成功",
        data=OrderCreateOut(
            order_id=order.id,
            order_no=order.order_no,
            pay_amount=float(order.pay_amount),
            status=order.status,
            created_at=order.created_at,
        ),
    )


@router.get("/list", description="我的订单列表")
async def req_order_list(
    status: str | None = Query(None, description="订单状态：paid/shipped/completed/canceled"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50, alias="pageSize"),
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    orders, total = await get_order_list(db, current.id, status, page, page_size)

    #一次把这一页的明细全查出来，避免每个订单查一次（N+1）
    grouped = await get_items_by_order_ids(db, [o.id for o in orders])
    data = [order_to_list_out(o, grouped.get(o.id, [])) for o in orders]

    return page_response(items=data, total=total, page=page, page_size=page_size)


@router.get("/detail", description="订单详情")
async def req_order_detail(
    order_no: str = Query(..., alias="orderNo", description="业务单号"),
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    order = await get_order_by_no(db, current.id, order_no)
    #别人的单号一律当"不存在"，不返回 403（避免泄露单号是否存在）
    if order is None:
        raise HTTPException(404, "订单不存在")

    items = await get_order_items(db, order.id)

    return success_response(
        message="success",
        data=OrderDetailOut(
            order_id=order.id,
            order_no=order.order_no,
            total_amount=float(order.total_amount),
            pay_amount=float(order.pay_amount),
            status=order.status,
            status_text=STATUS_TEXT.get(order.status, order.status),
            created_at=order.created_at,
            item_count=len(items),
            items=[item_to_out(i) for i in items],
            receiver_name=order.receiver_name,
            receiver_phone=order.receiver_phone,
            receiver_address=order.receiver_address,
            remark=order.remark,
            paid_at=order.paid_at,
            canceled_at=order.canceled_at,
        ),
    )


@router.put("/cancel", description="取消订单（回滚库存）")
async def req_cancel_order(
    body: OrderCancelSchema,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    order = await cancel_order(db, current.id, body.order_no)

    logger.info("用户 %s 取消订单 %s", current.username, order.order_no)

    return success_response(
        message="订单已取消",
        data={"orderNo": order.order_no, "status": order.status},
    )
