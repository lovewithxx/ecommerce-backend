import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.config.db_conf import get_db
from app.crud.product import get_product_by_id, get_product_count, get_product_list
from app.models.users import User
from app.schemas.product import ProductDetail, ProductList
from app.untils.auth import get_current_user
from app.untils.response import page_response, success_response

logger = logging.getLogger("ec_platform")

router = APIRouter(prefix="/api/product", tags=["商品"])


#商品列表
@router.get("/list", summary="获取商品列表")
async def get_pd_list(
    category_id: int | None = Query(None, alias="categoryId", description="分类ID，不传=全部"),
    keyword: str | None = Query(None, max_length=50, description="搜索词"),
    sort: Literal["default", "sales_desc", "price_asc", "price_desc"] = Query(
        "default",
        description="default=最新 / sales_desc=销量高到低 / price_asc=价格升 / price_desc=价格降",
    ),
    page: int = Query(1, ge=1, description="第几页，从 1 开始"),
    page_size: int = Query(12, ge=1, le=100, alias="pageSize", description="每页多少条"),
    db: AsyncSession = Depends(get_db),
):
    """
    首页：不传参数
    分类页：传 categoryId
    搜索结果：传 keyword，再传 sort 排序
    """
    offset = (page - 1) * page_size

    products = await get_product_list(
        db,
        category_id=category_id,
        keyword=keyword,
        sort=sort,
        skip=offset,
        limit=page_size,
    )
    total = await get_product_count(db, category_id=category_id, keyword=keyword)

    items = [ProductList.model_validate(product) for product in products]

    logger.info(
        "商品列表：categoryId=%s keyword=%s sort=%s page=%s total=%s",
        category_id, keyword, sort, page, total,
    )

    return page_response(
        items,
        total=total,
        page=page,
        page_size=page_size,
        message="获取商品列表成功",
    )


#商品详情，需登录
@router.get("/detail", summary="获取商品详情")
async def get_pd_detail(
    product_id: int = Query(..., alias="id", description="商品ID"),
    current: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db),
):
    product = await get_product_by_id(db, product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="商品不存在或已下架",
        )

    logger.info("用户 %s 查看商品 %s", current.username, product_id)

    return success_response(
        message="success",
        data=ProductDetail.model_validate(product),
    )