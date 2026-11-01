import logging
from fastapi import APIRouter, Depends,HTTPException,Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.db_conf import get_db
from app.crud.address import (
    add_address_in_table,
    delete_address,
    get_address,
    get_useraddress_list,
    set_default,
    update_address,
)
from app.models.address import Address
from app.models.users import User
from app.schemas.address import AddressCreateSchema, AddressOutSchema, AddressUpdateSchema
from app.untils.auth import get_current_user
from app.untils.response import success_response

logger = logging.getLogger("ec_platform")

router = APIRouter(prefix="/api/address", tags=["收货地址"])



def to_out(addr: Address) -> AddressOutSchema:
    return AddressOutSchema(
        id=addr.id,
        receiver_name=addr.receiver_name,
        receiver_phone=addr.receiver_phone,
        province=addr.province,
        city=addr.city,
        district=addr.district,
        detail=addr.detail,
        poi_name=addr.poi_name,
        full_address=f"{addr.province}{addr.city}{addr.district}{addr.detail}",
        lng=float(addr.lng) if addr.lng is not None else None,
        lat=float(addr.lat) if addr.lat is not None else None,
        is_default=(addr.is_default==1),
        created_at=addr.created_at,
    )




@router.post("/create", description="新增收货地址")
async def req_addaddress(body: AddressCreateSchema,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    addr = await add_address_in_table(db, current.id, body)
    logger.info("用户 %s 新增地址 %s", current.username, addr.id)
    return success_response(message="添加地址成功", data=to_out(addr))




@router.get("/list",description="获取地址列表")
async def req_get_addresslist(
        current: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    rows=await get_useraddress_list(db,current.id)
    res = [to_out(a) for a in rows]
    logger.info("获取用户%s的地址列表，共%d条",current.username,len(res))
    return success_response(message="获取地址列表成功",data=res)



@router.put("/set-default",description="设置默认")
async def set_address_default(id:int,current:User=Depends(get_current_user),db:AsyncSession=Depends(get_db)):
    addr = await set_default(db, current.id, id)
    if addr is None:
        raise HTTPException(404, "地址不存在")
    logger.info("用户 %s 设置默认地址 %s", current.username, addr.id)
    return success_response(message="设置成功",data=to_out(addr))




@router.put("/update", description="修改收货地址")
async def req_update_address(
    body: AddressUpdateSchema,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    #只传要改的字段
    addr = await get_address(db, current.id, body.id)
    if addr is None:
        raise HTTPException(404, "地址不存在")

    #exclude_unset：只取"用户真正传了"的字段
    changes = body.model_dump(exclude_unset=True, exclude={"id"})
    if not changes:
        raise HTTPException(400, "没有要修改的字段")

    addr = await update_address(db, current.id, addr, changes)

    logger.info("用户 %s 修改地址 %s，字段=%s", current.username, addr.id, list(changes.keys()))
    return success_response(message="修改成功", data=to_out(addr))




@router.delete("/delete", description="删除收货地址")
async def req_delete_address(
    id: int = Query(..., gt=0, description="地址ID"),
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """软删除。删掉的是默认地址时，会自动把最近的一条设为默认。"""
    addr = await get_address(db, current.id, id)
    if addr is None:
        raise HTTPException(404, "地址不存在")

    await delete_address(db, current.id, addr)

    logger.info("用户 %s 删除地址 %s", current.username, id)
    return success_response(message="已删除", data={"deleted": True})
