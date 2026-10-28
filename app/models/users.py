from datetime import datetime
from typing import Optional


from sqlalchemy import DateTime, ForeignKey, Index, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column


from app.models.base import Base


class User(Base):
    """
    用户信息表ORM模型
    """
    __tablename__ = 'user'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="用户ID")
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="用户名")
    password: Mapped[str] = mapped_column(String(255), nullable=False, comment="密码（加密存储），bcrypt 哈希，不存明文")
    nickname: Mapped[Optional[str]] = mapped_column(String(50), comment="昵称，业务层默认取username，数据库不设置default")
    avatar: Mapped[Optional[str]] = mapped_column(String(255), comment="头像URL，默认头像由前端兜底，数据库存null")
    gender: Mapped[str] = mapped_column(String(10), default="unknown", nullable=False, comment="性别 male/female/unknown")
    bio: Mapped[Optional[str]] = mapped_column(String(500), comment="个人简介，默认文案前端展示兜底")
    phone: Mapped[Optional[str]] = mapped_column(String(20), unique=True, comment="手机号")
    email: Mapped[Optional[str]] = mapped_column(String(100), unique=True, comment="邮箱，找回密码用")
    status: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False, comment="状态：1正常 0禁用")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', nickname='{self.nickname}')>"

 



class UserToken(Base):
    """
    用户令牌表。

    ★ 单设备登录：一个用户只允许有一条 token ★
      user_id 上是唯一索引，所以登录时是"更新那一条"，不是"新增一条"。
      旧设备的 token 被覆盖后，下次请求查不到记录 -> 401 -> 自动下线。

    好处：逻辑简单，永远只有一条。
    代价：手机和电脑不能同时在线，后登录的会把先登录的挤掉。
    """

    __tablename__ = 'user_token'

    __table_args__ = (
        # ★ 唯一索引：从数据库层面保证一个用户只有一条 token
        Index("uniq_user_token_user_id", "user_id", unique=True),
        # 过期清理时按时间筛
        Index("idx_user_token_expires_at", "expires_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="令牌ID")
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        comment="用户ID",
    )
    # secrets.token_hex(16) 产出32字节hex，字符串长度64
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, comment="32位十六进制令牌字符串")
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="令牌过期时间，签发时设置为当前+7天")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="令牌创建时间")

    def __repr__(self):
        return f"<UserToken(id={self.id}, user_id={self.user_id})>"
