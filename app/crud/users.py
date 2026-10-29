import secrets
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.users import User, UserToken
from app.untils.security import get_hash_password, verify_password


# token有效期（天）
TOKEN_TTL_DAYS = 7


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    """
    按用户名查用户。查不到返回 None。
    """
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    """按 ID 查用户。"""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()



#创建用户
async def create_user(
    db: AsyncSession,
    username: str,
    password: str,
    nickname: str | None = None,
) -> User:
    user = User(
        username=username,
        password=get_hash_password(password),
        nickname=nickname or username,
        gender="unknown",
        status=1,
    )
    db.add(user)
    await db.flush()      
    await db.refresh(user)  
    return user





async def issue_token(db: AsyncSession, user_id: int) -> tuple[str, datetime]:
    """
    签发 token，返回 (token 字符串, 过期时间)。
    """
    token = secrets.token_hex(16)     # 16 字节 -> 32 位十六进制字符串
    expires_at = datetime.now() + timedelta(days=TOKEN_TTL_DAYS)

    result = await db.execute(select(UserToken).where(UserToken.user_id == user_id))
    row = result.scalars().first()    # user_id 唯一，最多一条
    if row is None:
        db.add(UserToken(user_id=user_id, token=token, expires_at=expires_at))
    else:
        row.token = token             #覆盖旧 token
        row.expires_at = expires_at
    await db.flush()
    return token, expires_at


async def get_user_by_token(db: AsyncSession, token: str) -> User | None:
    """
    用 token 获取用户。token 无效或已过期都返回 None。
    """
    stmt = (
        select(User)
        .join(UserToken, UserToken.user_id == User.id)
        .where(
            UserToken.token == token,
            UserToken.expires_at > datetime.now(),   # 未过期
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def check_password(db: AsyncSession, username: str, password: str) -> User | None:
    """
    校验用户名 + 密码，成功返回 User，失败返回 None。
    """
    user = await get_user_by_username(db, username)
    if user is None:
        return None
    if not verify_password(password, user.password):
        return None
    return user


#修改用户信息
async def update_user(db: AsyncSession, user: User, changes: dict) -> User:
    for field, value in changes.items():
        setattr(user, field, value)
    await db.flush()          # 发 UPDATE，但不 commit（交给 get_db）
    await db.refresh(user)    # 读回最新值（updated_at 会变）
    return user


async def update_password(db: AsyncSession, user: User, new_password: str) -> None:
    """
    修改密码
    """
    user.password = get_hash_password(new_password)
    await db.flush()


async def revoke_all_tokens(db: AsyncSession, user_id: int) -> int:
    """
    删除该用户的令牌
    """
    result = await db.execute(delete(UserToken).where(UserToken.user_id == user_id))
    await db.flush()
    return result.rowcount or 0


async def revoke_token(db: AsyncSession, token: str) -> int:
    """
    按 token 字符串删除记录（退出登出）

    """
    result = await db.execute(delete(UserToken).where(UserToken.token == token))
    await db.flush()
    return result.rowcount or 0