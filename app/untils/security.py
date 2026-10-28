"""
密码哈希。

=====================================================================
【为什么必须哈希，不能存明文】
=====================================================================

bcrypt 的特点：
    1. 单向：只能加密，不能还原
    2. 自带盐（salt）：同一个密码每次哈希结果都不同，
       所以攻击者没法用"彩虹表"批量比对
    3. 故意慢：一次约 100ms。这是特性不是缺陷 ——
       让暴力破解每秒只能试十次，而不是几百万次

=====================================================================
【★ 为什么这里用同步 def，不加 async ★】
=====================================================================
你原来写的是 `async def get_hash_password(...)`，但函数体是纯 CPU 计算
（pwd_context.hash），里面没有任何 await。

写成 async def 不会让它变快，反而有害：
    async 函数在 await 之前是【独占事件循环】的。
    一次 bcrypt 约 100ms，这 100ms 里整个服务处理不了任何其他请求。
    并发 10 个人同时注册，就要排队 1 秒。

正确做法：
    保持同步 def，需要不阻塞时用 await asyncio.to_thread(...) 丢到线程里。
    本项目注册频率低，直接同步调用即可，简单清晰。

面试会问："你的密码怎么存的？" —— 答"bcrypt + 自动加盐"，
不要说"md5"或"sha256"，那两个对密码来说是错的（太快、无盐）。
=====================================================================
"""

from passlib.context import CryptContext

# schemes=["bcrypt"]：用 bcrypt 算法
# deprecated="auto"：将来换更强算法时，老哈希还能验证，登录后自动升级
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_hash_password(password: str) -> str:
    """
    明文 -> 哈希。返回的字符串形如：
        $2b$12$KIXQ...（60 个字符，包含算法标识、成本因子、盐、哈希值）
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    校验密码。返回 True / False。

    注意：verify 会自动从 hashed_password 里解析出盐，
    所以不需要你手动存盐 —— 盐已经包含在那 60 个字符里了。
    """
    return pwd_context.verify(plain_password, hashed_password)
