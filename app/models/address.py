#收货地址表

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    DECIMAL,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Address(Base):
    __tablename__ = 'address'

    __table_args__ = (
        Index("idx_address_user_id", "user_id"),
        Index("idx_address_user_default", "user_id", "is_default"),

        CheckConstraint("lng IS NULL OR (lng BETWEEN -180 AND 180)", name="ck_address_lng"),
        CheckConstraint("lat IS NULL OR (lat BETWEEN -90 AND 90)", name="ck_address_lat"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="地址ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id", ondelete="CASCADE"),nullable=False, comment="用户ID")
    receiver_name: Mapped[str] = mapped_column(String(50), nullable=False, comment="收货人姓名")
    receiver_phone: Mapped[str] = mapped_column(String(20), nullable=False, comment="收货人手机号")
    province: Mapped[str] = mapped_column(String(50), nullable=False, comment="省")
    city: Mapped[str] = mapped_column(String(50), nullable=False, comment="市")
    district: Mapped[str] = mapped_column(String(50), nullable=False, comment="区/县")
    detail: Mapped[str] = mapped_column(String(255), nullable=False, comment="详细地址（街道门牌）")
    # ---------------- 地图相关 ----------------
    poi_name: Mapped[Optional[str]] = mapped_column(String(100), comment="地点名称，如「万科大厦」，展示用")
    lng: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 7), comment="经度，-180 ~ 180")
    lat: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 7), comment="纬度，-90 ~ 90")

    is_default: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0",nullable=False, comment="是否默认：1是 0否")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now,server_default=func.now(), comment="更新时间")

    def __repr__(self):
        return f"<Address(id={self.id}, {self.receiver_name} {self.province}{self.city})>"
