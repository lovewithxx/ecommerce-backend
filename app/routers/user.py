"""
用户路由：注册 / 登录 / 退出 / 查看信息 / 修改信息 / 修改密码。

=====================================================================
【认证方式：HttpOnly Cookie】
=====================================================================
登录成功后，后端把 token 写进 Cookie（httponly=True），响应体里【不返回 token】。

四个接口都要注意 Cookie：
    注册 / 登录   -> set_cookie
    退出 / 改密码 -> delete_cookie
=====================================================================
"""

import logging

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.config.db_conf import get_db
from app.crud import users as crud_users
from app.models.users import User
from app.schemas.users import (
    LoginRequest,
    UserChangePassword,
    UserInfoResponse,
    UsersRequest,
    UserUpdateRequest,
)
from app.untils.auth import get_current_user
from app.untils.response import success_response
from app.untils.security import verify_password

logger = logging.getLogger("ec_platform")

router = APIRouter(prefix="/api/user", tags=["用户"])

# ---------------- Cookie 配置 ----------------
COOKIE_NAME = "access_token"
# ★ 本地开发是 HTTP，必须 False；上线走 HTTPS 必须改 True ★
#   设成 True 而本地是 http，浏览器会丢弃这个 cookie，表现为"登录成功但立刻 401"
COOKIE_SECURE = False
COOKIE_MAX_AGE = crud_users.TOKEN_TTL_DAYS * 24 * 3600   # 与 token 有效期一致


def _set_token_cookie(resp: Response, token: str) -> Response:
    resp.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,       # JS 读不到，防 XSS 窃取
        samesite="lax",      # 跨站 POST 不携带，防 CSRF
        secure=COOKIE_SECURE,
        path="/",
    )
    return resp


def _clear_token_cookie(resp: Response) -> Response:
    """
    删除 Cookie。

    """
    resp.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
    )
    return resp


# =========================================================================
# 注册
# =========================================================================
@router.post(
    "/register",
    summary="注册用户",
    description=(
        "注册成功即自动登录：token 写入HttpOnly Cookie，响应体里不返回 token。\n\n"
        "用户名规则：3~50 位，只能包含字母、数字、下划线\n\n"
        "密码规则：6~32 位，bcrypt 哈希后存储，数据库里看不到明文"
    ),
)
async def register(
    body: UsersRequest,
    db: AsyncSession = Depends(get_db),
):
    # 1. 查重
    if await crud_users.get_user_by_username(db, body.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在",
        )

    # 2. 建用户（密码哈希）
    user = await crud_users.create_user(
        db,
        username=body.username,
        password=body.password,
        nickname=body.nickname,
    )

    # 3. 签发 token
    token, _ = await crud_users.issue_token(db, user.id)

    logger.info("新用户注册成功：id=%s username=%s", user.id, user.username)

    # 4. 先建响应，再往这个响应上写 Cookie（原因见 _set_token_cookie 注释）
    resp = success_response(
        message="注册成功",
        data={"userInfo": UserInfoResponse.model_validate(user)},
    )
    return _set_token_cookie(resp, token)


# =========================================================================
# 登录
# =========================================================================
@router.post(
    "/login",
    summary="用户登录",
    description=(
        "token 写入HttpOnly Cookie，响应体里不返回 token。\n\n"
        "单设备登录：本次登录会覆盖上一次的 token，旧设备随之被踢下线。\n\n"
        "失败统一返回 400「用户名或密码错误」"
    ),
)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    user = await crud_users.check_password(db, body.username, body.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名或密码错误",
        )

    if user.status != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="该账号已被禁用",
        )

    token, _ = await crud_users.issue_token(db, user.id)

    logger.info("登录成功：id=%s username=%s", user.id, user.username)

    resp = success_response(
        message="登录成功",
        data={"userInfo": UserInfoResponse.model_validate(user)},
    )
    return _set_token_cookie(resp, token)


# =========================================================================
# 退出登录
# =========================================================================
@router.post("/logout", summary="退出登录")
async def logout(
    access_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    退出登录。
        cookie 存在   -> 顺手删掉数据库里那条 token
        cookie 不存在 -> 什么也不做
        两种情况都返回 200 并清掉 cookie
    """
    if access_token:
        await crud_users.revoke_token(db, access_token)

    logger.info("用户退出登录")
    resp = success_response(message="已退出登录")
    return _clear_token_cookie(resp)


# =========================================================================
# 查看当前用户信息
# =========================================================================
@router.get("/info", summary="获取当前登录用户信息")
async def get_info(current: User = Depends(get_current_user)):
    """
        200 -> 登录着，data 就是用户信息
        401 -> 没登录
    """
    return success_response(
        message="success",
        data=UserInfoResponse.model_validate(current),
    )


# =========================================================================
# 修改账号信息
# =========================================================================
@router.put(
    "/info",
    summary="修改账号信息",
    description="只传要修改的字段，没传的保持不变",
)
async def update_info(
    body: UserUpdateRequest,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # exclude_unset：只取"用户真正传了"的字段
    # 用 exclude_none 的话，用户传 {"bio": null} 想清空简介会失败
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="没有要修改的字段",
        )

    # 手机号/邮箱撞唯一索引会抛 IntegrityError，
    # 由 untils/exception.py 的处理器转成 400「手机号已被占用」
    user = await crud_users.update_user(db, current, changes)

    logger.info("用户修改信息：id=%s 字段=%s", user.id, list(changes.keys()))
    return success_response(
        message="修改成功",
        data=UserInfoResponse.model_validate(user),
    )


# =========================================================================
# 修改密码
# =========================================================================
@router.put(
    "/password",
    summary="修改密码",
    description=(
        "需要提供旧密码。修改成功后 token 会被删除、Cookie 也会被清掉，"
        "需要用新密码重新登录。"
    ),
)
async def change_password(
    body: UserChangePassword,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # 1. 校验旧密码
    if not verify_password(body.old_password, current.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="原密码错误",
        )

    # 2. 新密码不能和旧密码一样
    if body.old_password == body.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="新密码不能与原密码相同",
        )

    # 3. 写入新密码（内部哈希）
    await crud_users.update_password(db, current, body.new_password)

    # 4. 删掉数据库里的 token + 清掉浏览器 cookie
    await crud_users.revoke_all_tokens(db, current.id)

    logger.info("用户修改密码：id=%s", current.id)
    resp = success_response(message="密码修改成功，请用新密码重新登录")
    return _clear_token_cookie(resp)
