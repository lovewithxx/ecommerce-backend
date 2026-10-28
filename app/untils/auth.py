"""
鉴权依赖：从 HttpOnly Cookie 里解析 token，换出当前用户。

=====================================================================
【用法（任何需要登录的接口都这么写）】
=====================================================================
    @router.get("/info")
    async def get_info(current: User = Depends(get_current_user)):
        ...

FastAPI 会自动：
    1. 从 Cookie 里取 access_token
    2. 先执行 get_current_user
    3. 通过后把返回的 User 注入到 current 参数
    4. 失败时直接返回 401，不会进入接口函数

=====================================================================
【为什么用 Cookie 而不是请求头】
=====================================================================
token 存在 HttpOnly Cookie 里，前端 JS 读不到，XSS 偷不走。

代价：
    CSRF 风险要靠 SameSite=Lax 挡住（跨站 POST 不会带这个 cookie）。
    如果哪天必须设 SameSite=None（跨站共享），就得再加 CSRF Token。
=====================================================================
"""

from fastapi import Cookie, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.config.db_conf import get_db
from app.crud import users as crud_users
from app.models.users import User


async def get_current_user(
    access_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """从 Cookie 中解析出当前用户。"""

    # 1. 有没有这个 cookie
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少认证凭证，请先登录",
        )

    # 2. token 是否有效且未过期（过期判断在 crud 的 SQL 里）
    user = await crud_users.get_user_by_token(db, access_token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效或已过期的令牌，请重新登录",
        )

    # 3. 账号是否被禁用
    if user.status != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="该账号已被禁用",
        )

    return user
