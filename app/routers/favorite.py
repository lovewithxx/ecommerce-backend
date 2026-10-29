"""
收藏路由。

★ 四个接口全部要登录 ★
    POST   /api/favorite/add       请求体 {"productId": 1}
    DELETE /api/favorite/remove    ?productId=1
    GET    /api/favorite/list
    GET    /api/favorite/check     ?productId=1

★ user_id 从 current.id 取 ★

"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.config.db_conf import get_db
from app.crud.favorite import (
    add_favorite,
    get_favorite_list,
    is_favored,
    remove_favorite,
)
from app.crud.product import get_product_by_id
from app.models.users import User
from app.schemas.favorite import FavoriteItem, FavoriteRequest, FavoriteState
from app.untils.auth import get_current_user
from app.untils.response import success_response

logger = logging.getLogger("ec_platform")

router = APIRouter(prefix="/api/favorite", tags=["收藏"])


#收藏商品
@router.post("/add", summary="收藏商品")
async def add(
    body: FavoriteRequest,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    product = await get_product_by_id(db, body.product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="商品不存在或已下架",
        )

    created = await add_favorite(db, current.id, body.product_id)

    logger.info("用户 %s 收藏商品 %s（新增=%s）", current.username, body.product_id, created)

    return success_response(
        message="收藏成功" if created else "已经收藏过了",
        data=FavoriteState(favored=True),
    )


@router.delete("/remove", summary="取消收藏")
async def remove(
    product_id: int = Query(..., alias="productId", gt=0, description="商品ID"),
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    removed = await remove_favorite(db, current.id, product_id)

    logger.info("用户 %s 取消收藏商品 %s（删除=%s）", current.username, product_id, removed)

    return success_response(
        message="已取消收藏" if removed else "本来就没有收藏",
        data=FavoriteState(favored=False),
    )



#收藏列表
@router.get("/list", summary="我的收藏")
async def list_favorite(
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = await get_favorite_list(db, current.id)

    items = [
        FavoriteItem(
            id=product.id,
            name=product.name,
            subtitle=product.subtitle,
            cover=product.cover,
            price=product.price,
            original_price=product.original_price,
            stock=product.stock,
            sales=product.sales,
            category_id=product.category_id,
            favorited_at=favorited_at,
        )
        for product, favorited_at in rows
    ]

    return success_response(message="success", data=items)



#判断是否收藏
@router.get("/check", summary="是否已收藏")
async def check(
    product_id: int = Query(..., alias="productId", gt=0, description="商品ID"),
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    favored = await is_favored(db, current.id, product_id)
    return success_response(message="success", data=FavoriteState(favored=favored))
