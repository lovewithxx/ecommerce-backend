"""
商品路由：列表 + 详情。

=====================================================================
【一个列表接口，通过参数变形】
=====================================================================
    /api/product/list                      首页（全部商品）
    /api/product/list?categoryId=2         分类页
    /api/product/list?keyword=耳机          搜索
    /api/product/list?sort=price_asc       排序
    /api/product/list?page=2&pageSize=20    分页

不要为"首页 / 分类 / 搜索"写三个接口 ——
分页、总数、hasMore 的逻辑会重复三遍。
=====================================================================
"""

import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.config.db_conf import get_db
from app.crud.product import get_product_by_id, get_product_count, get_product_list
from app.schemas.product import ProductDetail, ProductList
from app.untils.response import page_response, success_response

logger = logging.getLogger("ec_platform")

router = APIRouter(prefix="/api/product", tags=["商品"])


@router.get("/list", summary="获取商品列表")
async def list_products(
    category_id: int | None = Query(None, alias="categoryId", description="分类ID，不传=全部"),
    keyword: str | None = Query(None, max_length=50, description="搜索关键词"),
    sort: Literal["default", "sales", "price_asc", "price_desc", "newest"] = Query("default", description="排序方式"),
    page: int = Query(1, ge=1, description="第几页，从 1 开始"),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize", description="每页多少条"),
    db: AsyncSession = Depends(get_db),
):
    """商品列表，支持分类筛选 / 关键词搜索 / 排序 / 分页。"""
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
    # ORM 对象 -> 响应 schema（schemas 里配了 from_attributes=True）
    items = [ProductList.model_validate(product) for product in products]

    logger.info(
        "商品列表：categoryId=%s keyword=%s page=%s total=%s",
        category_id, keyword, page, total,
    )

    return page_response(
        items, total=total, page=page, page_size=page_size,
        message="获取商品列表成功",
    )




@router.get("/detail", summary="获取商品详情")
async def get_product_detail(
    product_id: int = Query(..., alias="id", description="商品ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    单个商品详情，比列表多返回 description / specs / images。

    specs 和 images 在数据库里是 JSON 字符串，
    ProductDetail 上的 field_validator 会自动解析成对象，这里不用手动 json.loads。
    """
    product = await get_product_by_id(db, product_id)
    if product is None:
        # 这里用 404 是对的：确实"这个商品不存在"
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="商品不存在或已下架",
        )

    return success_response(
        message="success",
        data=ProductDetail.model_validate(product),
    )
