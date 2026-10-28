import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.db_conf import get_db
from app.crud.category import get_category_list, get_product_count_by_category
from app.schemas.category import CategoryList
from app.untils.response import success_response

logger = logging.getLogger("ec_platform")

router = APIRouter(prefix="/api/category", tags=["分类"])




@router.get("/list", summary="获取分类列表")
async def list_categories(
    skip: int = Query(0, ge=0, description="跳过多少条"),
    limit: int = Query(100, ge=1, le=200, description="最多返回多少条"),
    db: AsyncSession = Depends(get_db),
):
    categories = await get_category_list(db, skip, limit)
    items: list[CategoryList] = []
    for category in categories:
        product_count = await get_product_count_by_category(db, category.id)
        items.append(
            CategoryList(
                id=category.id,
                name=category.name,
                icon=category.icon,
                parentId=category.parent_id,
                sort=category.sort,
                productCount=product_count,
            )
        )
    logger.info("返回分类 %s 个", len(items))
    return success_response(message="获取分类列表成功", data=items)
