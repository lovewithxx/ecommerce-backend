"""
用户相关的请求体 / 响应体。
    请求体（Request）  前端传进来的数据，要严格校验
    响应体（Response） 后端返回的数据，控制"暴露哪些字段"
=====================================================================
【★ 请求体就是"白名单"，不要靠 if 判断挡越权字段 ★】
=====================================================================
UserUpdateRequest 里只有 nickname/avatar/gender/bio/phone/email。
用户如果偷偷在 body 里加 {"username":"hacker","status":0}，
Pydantic 默认 extra="ignore" 会直接丢掉 —— 请求体里没定义的字段，
根本进不了 model_dump()，也就改不了库。

这比在路由里写 `if "username" in body: raise` 可靠得多，
因为你不会忘、也不会漏。
=====================================================================
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# =========================================================================
# 请求体
# =========================================================================
class UsersRequest(BaseModel):
    """注册请求。"""
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_]+$",
        description="用户名，3~50 位，只能包含字母数字下划线",
        examples=["alice_01"],
    )
    password: str = Field(
        ...,
        min_length=6,
        max_length=32,
        description="密码，6~32 位",
        examples=["123456"],
    )
    nickname: Optional[str] = Field(
        None, max_length=50, description="昵称，不传默认取用户名"
    )


class LoginRequest(BaseModel):
    """
    登录请求。
    """
    username: str = Field(..., min_length=1, max_length=50, description="用户名")
    password: str = Field(..., min_length=1, max_length=32, description="密码")


class UserUpdateRequest(BaseModel):
    """
    修改账号信息。所有字段可选，只传要改的。
    """
    nickname: Optional[str] = Field(None, min_length=1, max_length=50, description="昵称")
    avatar: Optional[str] = Field(None, max_length=255, description="头像URL")
    gender: Optional[Literal["male", "female", "unknown"]] = Field(
        None, description="性别，只能是 male / female / unknown"
    )
    bio: Optional[str] = Field(None, max_length=500, description="个人简介")
    phone: Optional[str] = Field(
        None,
        pattern=r"^1[3-9]\d{9}$",
        description="手机号，11 位中国大陆号码",
    )
    email: Optional[str] = Field(
        None,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
        description="邮箱",
    )


class UserChangePassword(BaseModel):
    """修改密码。"""

    old_password: str = Field(..., alias="oldPassword", min_length=1, max_length=32, description="旧密码")
    new_password: str = Field(...,alias="newPassword",min_length=6,max_length=32,description="新密码，6~32 位",)
    model_config = ConfigDict(populate_by_name=True)


# =========================================================================
# 响应体
# =========================================================================
class UserInfoBase(BaseModel):
    """用户信息基础字段。"""

    nickname: Optional[str] = Field(None, max_length=50, description="昵称")
    avatar: Optional[str] = Field(None, max_length=255, description="头像URL")
    gender: Optional[str] = Field(None, max_length=10, description="性别")
    bio: Optional[str] = Field(None, max_length=500, description="个人简介")


class UserInfoResponse(UserInfoBase):
    """
    返回给前端的用户信息。
    """
    id: int
    username: str
    phone: Optional[str] = None
    email: Optional[str] = None
    created_at: Optional[datetime] = Field(None, alias="createdAt")

    model_config = ConfigDict(
        from_attributes=True,      # 允许直接从 ORM 对象读属性
        populate_by_name=True,
    )
