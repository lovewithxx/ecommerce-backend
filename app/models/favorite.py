"""
收藏表。

=====================================================================
【两个关键设计】
=====================================================================
1. 只存 user_id + product_id，不存商品名和价格
      价格会变、商品名会改，存快照迟早和 product 表对不上。
      列表接口用 JOIN 去 product 表现取。

2. 用唯一索引 (user_id, product_id) 防重复
      "同一个用户不能重复收藏同一个商品"交给数据库保证，
      而不是在代码里先查再插 —— 并发时那种写法会插进两条。
      重复收藏时数据库报 1062，捕获后当成"已收藏"处理即可。
=====================================================================
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Favorite(Base):
    """用户收藏。"""

    __tablename__ = 'favorite'

    __table_args__ = (
        # 一个用户对一个商品只能收藏一次
        UniqueConstraint("user_id", "product_id", name="uniq_favorite_user_product"),
        Index("idx_favorite_product_id", "product_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="收藏ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id", ondelete="CASCADE"),nullable=False, comment="用户ID")
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("product.id", ondelete="CASCADE"),nullable=False, comment="商品ID")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, server_default=func.now(), comment="收藏时间")

    def __repr__(self):
        return f"<Favorite(user_id={self.user_id}, product_id={self.product_id})>"
