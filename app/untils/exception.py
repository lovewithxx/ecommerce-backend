"""
全局异常处理器。把各种异常统一转成 {code, message, data} 格式。

=====================================================================
【为什么需要注册四个处理器，而不是一个 Exception】
=====================================================================
FastAPI / Starlette 的异常分几层，不同层的异常由不同中间件处理：

    ExceptionMiddleware（内层）
        ├─ HTTPException           -> 业务主动抛的（400/401/404）
        ├─ RequestValidationError  -> Pydantic 参数校验失败（422）
        └─ 自定义异常
    ServerErrorMiddleware（最外层）
        └─ Exception               -> 未预料到的崩溃（500）

如果只注册 Exception，业务抛的 HTTPException 会先被内层处理掉，
返回成 FastAPI 默认的 {"detail": "..."}，格式和我们的约定不一致。
所以要分别注册。

=====================================================================
【★ 一个容易踩的坑：要注册 starlette 的 HTTPException，不是 fastapi 的】
=====================================================================
fastapi.HTTPException 是 starlette.exceptions.HTTPException 的子类。
你写接口时抛的是 fastapi 那个（子类），
但框架自己产生的 404（路由不存在）用的是 starlette 那个（父类）。

只注册子类的话，框架 404 会漏掉，返回格式还是 {"detail": "Not Found"}。
所以这里注册父类 —— 注册父类能同时抓住子类。
=====================================================================
"""

import logging
import traceback

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette import status
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config.app_conf import settings

logger = logging.getLogger("ec_platform")


def _body(code: int, message: str, data=None) -> dict:
    return {"code": code, "message": message, "data": data}


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """业务异常：HTTPException(400, "用户名已存在") 这类。"""
    return JSONResponse(
        status_code=exc.status_code,
        content=_body(exc.status_code, str(exc.detail)),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    参数校验失败（422）。

    FastAPI 默认返回 {"detail": [{...}]}，不符合本项目格式，必须转一遍。
    这里把第一个错误压成一句人话，前端能直接展示。
    """
    errors = exc.errors()
    first = errors[0] if errors else {}
    # loc 形如 ("body", "password")，去掉 body 前缀
    location = ".".join(str(x) for x in first.get("loc", []) if x != "body")
    msg = first.get("msg", "参数不合法")
    message = f"参数校验失败：{location} {msg}" if location else f"参数校验失败：{msg}"

    return JSONResponse(
        status_code=422,     # 不用 status.HTTP_422_UNPROCESSABLE_ENTITY：新版 starlette 已标记为弃用
        content=_body(
            422,
            message,
            # 调试模式下把完整错误列表也返回，方便定位；生产环境不暴露
            jsonable_encoder(errors) if settings.debug else None,
        ),
    )


async def integrity_error_handler(request: Request, exc: IntegrityError):
    """
    数据库完整性约束冲突。

    最常见的是唯一索引冲突（用户名/手机号/邮箱重复）。
    注意：这个异常是【数据库层】抛的，说明应用层的查重没拦住
    （并发注册时两个请求同时通过了 username 查重）。
    所以处理器要能识别具体是哪个约束冲突。
    """
    raw = str(getattr(exc, "orig", exc))

    if "username" in raw:
        detail = "用户名已存在"
    elif "phone" in raw:
        detail = "手机号已被占用"
    elif "email" in raw:
        detail = "邮箱已被占用"
    elif "FOREIGN KEY" in raw:
        detail = "关联数据不存在"
    elif "Duplicate entry" in raw:
        detail = "数据已存在，请勿重复提交"
    else:
        detail = "数据约束冲突，请检查输入"

    logger.warning("IntegrityError: %s", raw[:300])

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=_body(
            400,
            detail,
            {"error_type": "IntegrityError", "detail": raw[:300]}
            if settings.debug else None,
        ),
    )


async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
    """其他数据库错误（连接断开、SQL 语法错等）。"""
    logger.error("SQLAlchemyError: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_body(
            500,
            "数据库操作失败，请稍后重试",
            {"error_type": type(exc).__name__, "detail": str(exc)[:500]}
            if settings.debug else None,
        ),
    )


async def general_exception_handler(request: Request, exc: Exception):
    """
    兜底：所有没被上面抓住的异常。

    ★ 生产环境绝对不要把 traceback 返回给前端 ★
    traceback 里可能有数据库密码、文件路径、依赖版本，
    是攻击者最喜欢的信息。调试模式打开，上线必须关。
    """
    logger.error("未处理异常: %s\n%s", exc, traceback.format_exc())
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_body(
            500,
            "服务器内部错误",
            {
                "error_type": type(exc).__name__,
                "detail": str(exc),
                "traceback": traceback.format_exc(),
            } if settings.debug else None,
        ),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """
    在 main.py 里调用一次。

    注册顺序不影响行为（Starlette 按异常类型精确匹配），
    但 Exception 必须最后兜底。
    """
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(IntegrityError, integrity_error_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_error_handler)
    app.add_exception_handler(Exception, general_exception_handler)
