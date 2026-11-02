"""
订单模块的请求体 / 响应体。

风格和 cart.py 一致：字段 snake_case + alias 驼峰，出参用 float 不用 Decimal
（Pydantic v2 会把 Decimal 序列化成字符串，前端 toFixed 会炸）。
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

# 状态 -> 中文，给前端直接显示
STATUS_TEXT = {
    "paid": "已支付",
    "shipped": "已发货",
    "completed": "已完成",
    "canceled": "已取消",
}


#直接购买时的单件商品
class OrderItemIn(BaseModel):
    product_id: int = Field(..., alias="productId", gt=0)
    quantity: int = Field(..., ge=1, le=99)
    model_config = ConfigDict(populate_by_name=True)


#创建订单请求
class OrderCreateSchema(BaseModel):
    """
    两种下单方式，二选一：

    方式一（购物车结算）：{"cartItemIds": [7, 8], ...}
    方式二（立即购买）  ：{"items": [{"productId": 1001, "quantity": 1}], ...}

    收货信息两种给法，二选一：
      - 传 addressId：后端从 address 表读出来**快照**进订单（推荐）
      - 传 receiverName / receiverPhone / receiverAddress 三个字段
    """

    cart_item_ids: Optional[List[int]] = Field(None, alias="cartItemIds", description="购物车行ID列表")
    items: Optional[List[OrderItemIn]] = Field(None, description="直接购买的商品列表")

    address_id: Optional[int] = Field(None, alias="addressId", gt=0, description="收货地址ID")

    receiver_name: Optional[str] = Field(None, alias="receiverName", max_length=50)
    receiver_phone: Optional[str] = Field(None, alias="receiverPhone", max_length=20)
    receiver_address: Optional[str] = Field(None, alias="receiverAddress", max_length=255)

    remark: Optional[str] = Field(None, max_length=255, description="买家备注")

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def check_payload(self):
        has_cart = bool(self.cart_item_ids)
        has_items = bool(self.items)

        # 两个都没传 / 都传了，都不行
        if has_cart == has_items:
            raise ValueError("cartItemIds 和 items 必须二选一")

        # 收货信息：addressId 或 三个字段齐
        if self.address_id is None:
            if not (self.receiver_name and self.receiver_phone and self.receiver_address):
                raise ValueError("收货信息不完整：传 addressId，或传 receiverName/receiverPhone/receiverAddress")
        return self


#取消订单请求
class OrderCancelSchema(BaseModel):
    order_no: str = Field(..., alias="orderNo", min_length=1, max_length=32)
    model_config = ConfigDict(populate_by_name=True)


#订单里的一行商品（快照）
class OrderItemOut(BaseModel):
    product_id: int = Field(alias="productId")
    product_name: str = Field(alias="productName")
    product_cover: Optional[str] = Field(None, alias="productCover")
    price: float
    quantity: int
    subtotal: float
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


#下单成功的返回
class OrderCreateOut(BaseModel):
    order_id: int = Field(alias="orderId")
    order_no: str = Field(alias="orderNo")
    pay_amount: float = Field(alias="payAmount")
    status: str
    created_at: datetime = Field(alias="createdAt")
    model_config = ConfigDict(populate_by_name=True)


#订单列表里的一项（items 只带前 3 条）
class OrderListOut(BaseModel):
    order_no: str = Field(alias="orderNo")
    pay_amount: float = Field(alias="payAmount")
    status: str
    status_text: str = Field(alias="statusText")
    created_at: datetime = Field(alias="createdAt")
    item_count: int = Field(alias="itemCount")
    items: List[OrderItemOut]
    model_config = ConfigDict(populate_by_name=True)


#订单详情（列表字段 + 收货信息 + 完整明细）
class OrderDetailOut(OrderListOut):
    order_id: int = Field(alias="orderId")
    total_amount: float = Field(alias="totalAmount")
    receiver_name: str = Field(alias="receiverName")
    receiver_phone: str = Field(alias="receiverPhone")
    receiver_address: str = Field(alias="receiverAddress")
    remark: Optional[str] = None
    paid_at: Optional[datetime] = Field(None, alias="paidAt")
    canceled_at: Optional[datetime] = Field(None, alias="canceledAt")
