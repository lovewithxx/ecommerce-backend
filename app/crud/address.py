from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models.address import Address
from app.schemas.address import AddressCreateSchema

MAX_ADDRESS = 20 #最多20个


#计算该用户现有地址数
async def count_address(db: AsyncSession, user_id: int) -> int:
    count = await db.scalar(
        select(func.count(Address.id)).where(Address.user_id == user_id)
    )
    return count or 0




#把该用户所有默认地址取消掉
async def clear_default(db: AsyncSession, user_id: int) -> None:
    await db.execute(
        update(Address)
        .where(Address.user_id == user_id, Address.is_default == 1)
        .values(is_default=0)
    )




#加入地址
async def add_address_in_table(db: AsyncSession,user_id: int,body: AddressCreateSchema)->Address:
    #数量上限
    count = await count_address(db, user_id)
    if count >= MAX_ADDRESS:
        raise HTTPException(status_code=400, detail=f"地址数量已达上限（{MAX_ADDRESS} 个）")
    #第一条地址强制默认（地址数量为0和用户没设置默认时）
    is_default = body.is_default or count == 0
    #如要设默认就先清掉旧默认
    if is_default:
        await clear_default(db, user_id)
    new_addr = Address(
        user_id=user_id,
        receiver_name=body.receiver_name,
        receiver_phone=body.receiver_phone,
        province=body.province,
        city=body.city,
        district=body.district,
        detail=body.detail,
        poi_name=body.poi_name,
        lng=body.lng,
        lat=body.lat,
        is_default=1 if is_default else 0,
    )
    db.add(new_addr)
    await db.flush()
    return new_addr




#设置默认
async def set_default(db: AsyncSession, user_id: int, address_id: int) -> Address|None:
    addr = await db.scalar(
        select(Address).where(Address.id == address_id,Address.user_id == user_id)
    )
    if addr is None:
        return None
    await clear_default(db, user_id)
    addr.is_default = 1
    await db.flush()
    return addr




#获取用户地址列表（默认地址排最前）
async def get_useraddress_list(db:AsyncSession,user_id:int)->list[Address]:
    stmt=select(Address).where(Address.user_id==user_id).order_by(Address.created_at.desc())
    result=await db.execute(stmt)
    return list(result.scalars().all())




#按 id 取地址
async def get_address(db: AsyncSession, user_id: int, address_id: int) -> Address | None:
    return await db.scalar(
        select(Address).where(
            Address.id == address_id,
            Address.user_id == user_id,
        )
    )




#修改地址：只改 changes 里有的字段
async def update_address(db: AsyncSession, user_id: int, addr: Address, changes: dict) -> Address:
    if changes.pop("is_default", None) is True:
        await clear_default(db, user_id)
        addr.is_default = 1
    for field, value in changes.items():
        setattr(addr, field, value)

    await db.flush()
    return addr




#删除地址，如果删的是默认地址，把剩下最近的一条顶上来
async def delete_address(db: AsyncSession, user_id: int, addr: Address) -> None:
    was_default = addr.is_default == 1

    await db.delete(addr)          
    await db.flush()

    if was_default:
        other = await db.scalar(
            select(Address)
            .where(Address.user_id == user_id)
            .order_by(Address.created_at.desc())
            .limit(1)
        )
        if other is not None:
            other.is_default = 1
            await db.flush()
