"""
收藏的请求体 / 响应体。
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

#收藏 / 取消收藏的请求体：{"productId": 123}
class FavoriteRequest(BaseModel):


    product_id: int = Field(..., alias="productId", gt=0)

    model_config = ConfigDict(populate_by_name=True)



#响应体，响应收藏列表信息
class FavoriteItem(BaseModel):
    id: int
    name: str
    subtitle: Optional[str] = None
    cover: Optional[str] = None
    price: float
    original_price: Optional[float] = Field(None, alias="originalPrice")
    stock: int
    sales: int
    category_id: int = Field(alias="categoryId")
    favorited_at: datetime = Field(..., alias="favoritedAt")

    model_config = ConfigDict(populate_by_name=True)


#响应体，返回收藏状态
class FavoriteState(BaseModel):
    favored: bool
