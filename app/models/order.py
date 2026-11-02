"""
订单与订单明细的 ORM 模型。
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    DECIMAL,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


#订单主表
class Order(Base):
    __tablename__ = 'order'

    __table_args__ = (
        #业务单号唯一（对外展示用，不暴露自增 id）
        UniqueConstraint("order_no", name="uniq_order_order_no"),
        Index("idx_order_user_status", "user_id", "status"),
        Index("idx_order_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="订单ID")
    order_no: Mapped[str] = mapped_column(String(32), nullable=False, comment="业务单号，如 20261101213000123456")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, comment="下单用户ID")
    total_amount: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False, comment="商品总额（元）")
    pay_amount: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False, comment="实付金额（元），当前等于总额")
    #status 取值：paid(下单即支付) / shipped(已发货) / completed(已完成) / canceled(已取消)
    #本项目不做支付接口，所以没有 pending_payment 这个状态
    status:Mapped[str] = mapped_column(String(20), nullable=False,default="paid",server_default="paid",comment="订单状态：paid/shipped/completed/canceled")

    receiver_name: Mapped[str] = mapped_column(String(50), nullable=False, comment="收货人（快照）")
    receiver_phone: Mapped[str] = mapped_column(String(20), nullable=False, comment="收货电话（快照）")
    receiver_address: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="收货地址（快照，省市区+详细地址拼好）"
    )

    remark: Mapped[Optional[str]] = mapped_column(String(255), comment="买家备注")
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="支付时间（= 下单时间，为将来接真实支付留位）")
    canceled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="取消时间")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, server_default=func.now(), comment="下单时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, server_default=func.now(), comment="更新时间")

    def __repr__(self):
        return f"<Order(id={self.id}, no='{self.order_no}', amount={self.pay_amount}, status='{self.status}')>"


#订单明细
class OrderItem(Base):
    __tablename__ = 'order_item'

    __table_args__ = (
        Index("idx_order_item_order_id", "order_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="明细ID")

    #明细跟着订单走：订单删了，明细一起删
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("order.id", ondelete="CASCADE"), nullable=False, comment="订单ID"
    )

    
    #不建外键,商品可能被下架甚至物理删除，但历史订单必须留着当时的商品信息
    product_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="商品ID（不建外键，商品删了订单也要保留）")

    #---------- 商品快照 ----------
    product_name: Mapped[str] = mapped_column(String(200), nullable=False, comment="商品名（快照）")
    product_cover: Mapped[Optional[str]] = mapped_column(String(255), comment="商品主图（快照）")
    price: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False, comment="下单时单价（快照，元）")

    quantity: Mapped[int] = mapped_column(Integer, nullable=False, comment="购买数量")
    subtotal: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False, comment="小计 = price * quantity（元）")

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, server_default=func.now(), comment="创建时间"
    )

    def __repr__(self):
        return f"<OrderItem(id={self.id}, order_id={self.order_id}, name='{self.product_name}', qty={self.quantity})>"
