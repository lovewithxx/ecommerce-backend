"""
商品与分类的 ORM 模型。
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
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

#商品分类
class Category(Base):

    __tablename__ = 'category'

    __table_args__ = (
        Index("idx_category_parent_id", "parent_id"),
        Index("idx_category_sort", "sort"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="分类ID")
    name: Mapped[str] = mapped_column(String(50), nullable=False, comment="分类名")
    icon: Mapped[Optional[str]] = mapped_column(String(255), comment="图标URL或emoji")
    parent_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False,comment="父分类ID，0表示一级分类（预留两级）")
    sort: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="排序，数字小的在前")
    status: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False, comment="状态：1显示 0隐藏")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now,server_default=func.now(), comment="更新时间")

    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}')>"


#商品
class Product(Base):

    __tablename__ = 'product'

    __table_args__ = (
        Index("idx_product_category_id", "category_id"),
        Index("idx_product_status", "status"),
        Index("idx_product_price", "price"),
        Index("idx_product_sales", "sales"),
        Index("idx_product_name", "name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="商品ID")
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("category.id"), nullable=False, comment="分类ID")
    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="商品名")
    subtitle: Mapped[Optional[str]] = mapped_column(String(255), comment="副标题/卖点")
    description: Mapped[Optional[str]] = mapped_column(Text, comment="商品详情（RAG 语料主要来源）")
    specs: Mapped[Optional[str]] = mapped_column(Text, comment="规格参数，JSON 字符串，如 {\"屏幕\":\"6.7英寸\"}")
    cover: Mapped[Optional[str]] = mapped_column(String(255), comment="主图URL")
    images: Mapped[Optional[str]] = mapped_column(Text, comment="图集，JSON 数组字符串")
    price: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False, comment="售价（元）")
    original_price: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 2), comment="原价（元），划线价用")
    stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="库存")
    sales: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="销量")
    status: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False, comment="状态：1上架 0下架")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now,server_default=func.now(), comment="更新时间")

    def __repr__(self):
        return f"<Product(id={self.id}, name='{self.name}', price={self.price})>"
