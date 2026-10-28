"""
统一的 ORM 基类。

"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """所有 ORM 模型的基类，全局唯一。"""
    pass
