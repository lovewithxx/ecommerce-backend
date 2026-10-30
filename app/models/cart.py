from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, UniqueConstraint, func,Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base



class Cart(Base):
    __tablename__="cart"
    __table_args__ = (
            UniqueConstraint("user_id", "product_id", name="uniq_cart_user_product"),
            Index("idx_cart_product_id", "product_id"),
        )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="购物车ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id", ondelete="CASCADE"),nullable=False, comment="用户ID")
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("product.id", ondelete="CASCADE"),nullable=False, comment="商品ID")
    quantity:Mapped[int]=mapped_column(Integer,nullable=False,default=1,comment="商品数量")
    selected:Mapped[bool]=mapped_column(Boolean,default=True,nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, server_default=func.now(), comment="加入时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now,server_default=func.now(), comment="更新时间")