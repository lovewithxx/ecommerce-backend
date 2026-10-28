"""
统一响应封装。所有接口的出口都在这里。

"""

from typing import Any

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


def success_response(message: str = "success", data: Any = None) -> JSONResponse:
    """
    成功响应。HTTP 200 + code 200。

    jsonable_encoder 的作用：
        把 Pydantic 模型、datetime、Decimal、ORM 对象等
        统一转换成能序列化成 JSON 的基础类型。
        有它就不用手写 .model_dump() 和 .isoformat()。
    """
    content = {"code": 200, "message": message, "data": data}
    return JSONResponse(status_code=200, content=jsonable_encoder(content))


def error_response(code: int, message: str, data: Any = None) -> JSONResponse:
    """
    失败响应。HTTP 状态码和 code 保持一致。

    一般不需要手动调用 —— 抛 HTTPException 后由
    app/untils/exception.py 里的处理器统一转成这个格式。
    只有"需要在正常流程里主动返回错误"时才直接用它。
    """
    content = {"code": code, "message": message, "data": data}
    return JSONResponse(status_code=code, content=jsonable_encoder(content))


def page_response(
    items: list,
    total: int,
    page: int,
    page_size: int,
    message: str = "success",
) -> JSONResponse:
    """
    分页响应。格式沿用旧项目，额外回显 page / pageSize 方便前端。

    hasMore 的判断：total > page * page_size
        例：total=37, page=1, pageSize=10 -> 37 > 10 -> True
            total=37, page=4, pageSize=10 -> 37 > 40 -> False
    """
    data = {
        "list": items,
        "total": total,
        "hasMore": total > page * page_size,
        "page": page,
        "pageSize": page_size,
    }
    return success_response(message=message, data=data)
