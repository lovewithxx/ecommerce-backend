
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field





#=====================================#
#请求体

















#=========================================#
#响应体
class CategoryList(BaseModel):
    id:int
    name:str
    icon:Optional[str]=None
    parentId:int
    sort:int
    productCount:int
