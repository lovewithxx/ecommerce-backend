import json
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProductList(BaseModel):
    id: int
    name: str
    subtitle: Optional[str] = None
    cover: Optional[str] = None
    price: float
    original_price: Optional[float] = Field(None, alias="originalPrice")

    stock: int
    sales: int
    category_id: int = Field(alias="categoryId")

    model_config = ConfigDict(
        from_attributes=True,     # 允许 ProductList.model_validate(ORM对象)
        populate_by_name=True,    # 字段名和 alias 都能用
    )


class ProductDetail(ProductList):
    """详情：在列表基础上多返回长文本和规格。"""

    description: Optional[str] = None
    specs: Optional[dict[str, Any]] = None
    images: Optional[list[str]] = None
    status: int

    @field_validator("specs", "images", mode="before")
    @classmethod
    def _parse_json_string(cls, value):
        """
        数据库里 specs / images 存的是 JSON 字符串，
        这里在校验之前先解析成对象，否则 Optional[dict] 收到 str 会校验失败。

        mode="before" 意思是：在 Pydantic 做类型校验【之前】先跑这个函数。
        """
        if isinstance(value, str):
            if not value.strip():
                return None
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return value
