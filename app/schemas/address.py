"""
收货地址的请求体 / 响应体。
"""

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# 手机号正则
PHONE_REGEX = re.compile(r"^1[3-9]\d{9}$")


class AddressCreateSchema(BaseModel):
    """新增收货地址"""

    receiver_name: str = Field(alias="receiverName", min_length=1, max_length=32)
    receiver_phone: str = Field(alias="receiverPhone")
    province: str = Field(min_length=1, max_length=32)
    city: str = Field(min_length=1, max_length=32)
    district: str = Field(min_length=1, max_length=32)
    detail: str = Field(min_length=1, max_length=255)
    poi_name: Optional[str] = Field(None, alias="poiName", max_length=128)

    # ge / le 直接做范围校验，比手写 validator 少两段代码，报错信息也更清楚
    lng: Optional[float] = Field(None, ge=-180, le=180, description="经度")
    lat: Optional[float] = Field(None, ge=-90, le=90, description="纬度")

    is_default: bool = Field(False, alias="isDefault")

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("receiver_phone")
    @classmethod
    def check_phone(cls, v: str) -> str:
        if not PHONE_REGEX.fullmatch(v):
            raise ValueError("手机号格式不正确")
        return v


class AddressUpdateSchema(BaseModel):
    """
    修改收货地址：所有字段可选，只改传了的那些。

    ★ id 必传；判断"哪些字段要改"靠 model_dump(exclude_unset=True) ★
      用 exclude_none 的话，用户传 {"poiName": null} 想清空地点名会失败。
    """

    id: int = Field(..., gt=0)

    receiver_name: Optional[str] = Field(None, alias="receiverName", min_length=1, max_length=32)
    receiver_phone: Optional[str] = Field(None, alias="receiverPhone")
    province: Optional[str] = Field(None, min_length=1, max_length=32)
    city: Optional[str] = Field(None, min_length=1, max_length=32)
    district: Optional[str] = Field(None, min_length=1, max_length=32)
    detail: Optional[str] = Field(None, min_length=1, max_length=255)
    poi_name: Optional[str] = Field(None, alias="poiName", max_length=128)
    lng: Optional[float] = Field(None, ge=-180, le=180)
    lat: Optional[float] = Field(None, ge=-90, le=90)
    is_default: Optional[bool] = Field(None, alias="isDefault")

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("receiver_phone")
    @classmethod
    def check_phone(cls, v: Optional[str]) -> Optional[str]:
        # 没传手机号就不校验
        if v is None:
            return v
        if not PHONE_REGEX.fullmatch(v):
            raise ValueError("手机号格式不正确")
        return v


class AddressOutSchema(BaseModel):
    """返回给前端的地址对象"""

    id: int
    receiver_name: str = Field(alias="receiverName")
    receiver_phone: str = Field(alias="receiverPhone")
    province: str
    city: str
    district: str
    detail: str
    poi_name: Optional[str] = Field(None, alias="poiName")

    # full_address 不是表里的字段，是后端拼出来的，所以不能直接 model_validate(ORM对象)
    full_address: str = Field(alias="fullAddress")

    lng: Optional[float] = None
    lat: Optional[float] = None
    is_default: bool = Field(alias="isDefault")
    created_at: datetime = Field(alias="createdAt")     # ★ datetime，不是 str

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
