"""
商品的响应体。

=====================================================================
【为什么字段名用 snake_case + alias】
=====================================================================
ORM 属性叫 original_price / category_id。
Pydantic 字段如果直接写 camelCase（originalPrice），就没法和 ORM 属性对应，
`model_validate(product)` 会报"对象上没有这个属性"。

字段名跟 ORM 一致 + alias 指定对外名字，两边都能满足。
=====================================================================
"""

import json
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProductList(BaseModel):
    """列表项。★ 不含 description ★ 长文本只在详情返回，列表带上会白占流量。"""

    id: int
    name: str
    subtitle: Optional[str] = None
    cover: Optional[str] = None

    # ★ 价格用 float，不用 Decimal ★
    #   数据库是 DECIMAL(10,2)，查询出来是 Decimal；
    #   但 Pydantic v2 序列化 Decimal 时默认输出【字符串】"169.58"，
    #   前端 price.toFixed(2) 会直接报错（字符串没有 toFixed）。
    #   这里只做展示，float 足够；真正的金额计算在后端仍然用 Decimal。
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
