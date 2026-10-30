from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter,Depends,HTTPException,Query
from app.config.db_conf import get_db
from app.untils.response import success_response
from app.untils.auth import get_current_user
from app.crud.cart import (
    add_cart_item,
    clear_cart,
    get_cart_item_by_id,
    get_cart_item_by_user_product,
    get_cart_list,
    remove_cart_items,
    update_cart_item,
)
from app.crud.product import get_product_by_id
from app.models.users import User
from app.schemas.cart import Addcartrequest,Updatecartrequest



router=APIRouter(prefix="/api/cart",tags=["购物车"])



@router.post("/add",description="添加商品到购物车")
async def add_product_to_cart(body:Addcartrequest,
                              current:User=Depends(get_current_user),
                              db:AsyncSession=Depends(get_db)):
    #1 商品要存在且上架
    product=await get_product_by_id(db,body.product_id)
    if product is None or product.status!=1:
        raise HTTPException(404,"商品不存在或已下架")

    #2 已有数量+本次数量 不能超过库存
    exist=await get_cart_item_by_user_product(db,current.id,body.product_id)
    want=(exist.quantity if exist else 0)+body.quantity
    if want>product.stock:
        raise HTTPException(400,f"库存不足，最多还能买 {product.stock} 件")

    #3 写库
    cart=await add_cart_item(db,current.id,body.product_id,body.quantity)
    data={"cartItemId":cart.id, "quantity":cart.quantity}
    return success_response(message="添加商品到购物车成功",data=data)




@router.get("/list",description="获取购物车列表")
async def reget_cart_list(db:AsyncSession=Depends(get_db),
                          current:User=Depends(get_current_user)):
    rows=await get_cart_list(db,current.id)      #全部商品

    items=[]
    total_count=0
    selected_count=0
    total_amount=0
    for row in rows:
        subtotal=round(float(row.price)*row.quantity,2)
        total_count+=row.quantity
        #只有勾选的才计入结算金额
        if row.selected:
            selected_count+=row.quantity
            total_amount+=subtotal
        items.append({
            "id":row.id,
            "productId":row.product_id,
            "name":row.name,
            "cover":row.cover,
            "price":float(row.price),
            "stock":row.stock,
            "quantity":row.quantity,
            "selected":row.selected,
            "subtotal":subtotal,
            "invalid":row.quantity>row.stock,
        })

    data={
        "list":items,
        "totalCount":total_count,
        "selectedCount":selected_count,
        "totalAmount":round(total_amount,2),
    }
    return success_response(message="获取购物车列表成功",data=data)




@router.put("/update",description="改数量 / 改勾选")
async def update_cart(body:Updatecartrequest,
                      current:User=Depends(get_current_user),
                      db:AsyncSession=Depends(get_db)):
    #★ 只能改自己的购物车 ★ 查的时候带上 user_id
    cart_item=await get_cart_item_by_id(db,current.id,body.id)
    if cart_item is None:
        raise HTTPException(404,"购物车里没有这条记录")

    #数量改成 0 就删掉这条
    if body.quantity == 0:
        await remove_cart_items(db,current.id,[cart_item.id])
        return success_response(message="已从购物车移除",data={"removed":True})

    #改数量时要校验库存
    if body.quantity is not None:
        product=await get_product_by_id(db,cart_item.product_id)
        if product is None:
            raise HTTPException(404,"商品不存在或已下架")
        if body.quantity>product.stock:
            raise HTTPException(400,f"库存不足，最多还能买 {product.stock} 件")

    cart_item=await update_cart_item(db,cart_item,body.quantity,body.selected)
    data={"id":cart_item.id,"quantity":cart_item.quantity,"selected":cart_item.selected}
    return success_response(message="修改成功",data=data)




@router.delete("/remove",description="移出购物车（可批量）")
async def remove_cart(ids:str=Query(...,description="购物车行ID，逗号分隔，如 7,8,9"),
                      current:User=Depends(get_current_user),
                      db:AsyncSession=Depends(get_db)):
    #把 "7,8,9" 解析成 [7,8,9]
    id_list=[]
    for part in ids.split(","):
        part=part.strip()
        if not part:
            continue
        if not part.isdigit():
            raise HTTPException(400,f"ids 格式不对：{part} 不是数字")
        id_list.append(int(part))

    if not id_list:
        raise HTTPException(400,"ids 不能为空")

    removed=await remove_cart_items(db,current.id,id_list)
    return success_response(message=f"已移出 {removed} 件商品",data={"removed":removed})




@router.delete("/clear",description="清空购物车")
async def clear(current:User=Depends(get_current_user),
                db:AsyncSession=Depends(get_db)):
    removed=await clear_cart(db,current.id)
    return success_response(message=f"已清空 {removed} 件商品",data={"removed":removed})
