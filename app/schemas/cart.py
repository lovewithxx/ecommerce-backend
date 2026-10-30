from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


#添加商品请求
class Addcartrequest(BaseModel):
    product_id: int=Field(..., alias="productId",gt=0)
    quantity: int=Field(1, ge=1,le=99)
    model_config=ConfigDict(populate_by_name=True)


#更新请求：改数量 或 改勾选，二选一
#id是购物车行的id
class Updatecartrequest(BaseModel):
    id:int=Field(..., gt=0, description="购物车行ID")
    quantity:Optional[int]=Field(None, ge=0, le=99, description="改成几个，0 表示删除")
    selected:Optional[bool]=Field(None, description="是否勾选")
    model_config=ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def check_at_least_one(self):
        if self.quantity is None and self.selected is None:
            raise ValueError("quantity 和 selected 至少要传一个")
        return self




#返回列表响应
class Addcartlistresponse(BaseModel):
    id: int
    product_id:int=Field(alias="productId")
    name:str
    cover:Optional[str]=None
    price:float
    stock:int
    quantity:int
    selected:bool
    subtotal:float
    invalid:bool
    model_config=ConfigDict(from_attributes=True,populate_by_name=True)


class Addcartresponse(BaseModel):
    list:List[Addcartlistresponse]
    total_count:int=Field(alias="totalCount")
    selected_count:int=Field(alias="selectedCount")
    total_amount:float=Field(alias="totalAmount")
    model_config=ConfigDict(populate_by_name=True)
#     {
#   "list": [
#     { "id": 7, "productId": 1001, "name": "XX 手机", "cover": "...",
#       "price": 2999.00, "stock": 50, "quantity": 2,
#       "selected": true, "subtotal": 5998.00, "invalid": false }
#   ],
#   "totalCount": 2,
#   "selectedCount": 2,
#   "totalAmount": 5998.00
# }
