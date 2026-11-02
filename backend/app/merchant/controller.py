"""商户与商品 HTTP 接口。"""
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select, or_
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.merchant import schema, service
from app.merchant.model import Merchant, Product, MerchantMembership
from app.identity.controller import current_user, optional_user
from app.identity.permissions import require_merchant, require_platform_admin, owned_merchant_ids, is_platform_admin

router = APIRouter(prefix="/api/v1", tags=["商户与商品"])

@router.post("/merchants", summary="创建商户", response_model=schema.MerchantRead, status_code=201)
def create_merchant(data: schema.MerchantCreate, db: Session = Depends(get_db), user = Depends(current_user)):
    """创建一条商户记录。"""
    require_platform_admin(db, user)
    item = Merchant(**data.model_dump())
    db.add(item); db.flush()
    db.add(MerchantMembership(merchant_id=item.id, user_id=user.id, role='admin', status='active'))
    db.commit(); db.refresh(item)
    return item

@router.get("/merchants", summary="分页查询商户", response_model=list[schema.MerchantRead])
def list_merchants(offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db), user = Depends(optional_user)):
    """分页返回商户列表。"""
    query = select(Merchant)
    if not user or not is_platform_admin(db, user):
        query = query.where(or_(Merchant.status == 'active', Merchant.id.in_(owned_merchant_ids(user))))
    return list(db.scalars(query.order_by(Merchant.id).offset(offset).limit(limit)))

@router.get("/merchants/{item_id}", summary="查询商户详情", response_model=schema.MerchantRead)
def get_merchant(item_id: int, db: Session = Depends(get_db), user = Depends(optional_user)):
    """按 ID 获取商户详情。"""
    item = service.require(db, Merchant, item_id)
    if item.status != 'active' and not (user and is_platform_admin(db, user)):
        if user is None: raise HTTPException(404, '资源不存在')
        require_merchant(db, user, item.id, admin=False)
    return item

@router.patch("/merchants/{item_id}", summary="修改商户", response_model=schema.MerchantRead)
def update_merchant(item_id: int, data: schema.MerchantUpdate, db: Session = Depends(get_db), user = Depends(current_user)):
    """按 ID 部分更新商户信息。"""
    require_merchant(db, user, item_id)
    return service.update_item(db, Merchant, item_id, data)

@router.delete("/merchants/{item_id}", summary="删除商户", status_code=204)
def delete_merchant(item_id: int, db: Session = Depends(get_db), user = Depends(current_user)):
    """商户存在关联商品时拒绝删除，否则删除商户。"""
    require_merchant(db, user, item_id)
    service.delete_merchant(db, item_id)
    return Response(status_code=204)

@router.post("/products", summary="创建商品", response_model=schema.ProductRead, status_code=201)
def create_product(data: schema.ProductCreate, db: Session = Depends(get_db), user = Depends(current_user)):
    """检查所属商户存在后创建商品。"""
    service.require(db, Merchant, data.merchant_id)
    require_merchant(db, user, data.merchant_id)
    return service.create_product(db, data)

@router.get("/products", summary="分页查询商品", response_model=list[schema.ProductRead])
def list_products(offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db), user = Depends(optional_user)):
    """分页返回商品列表。"""
    query = select(Product).join(Merchant, Merchant.id == Product.merchant_id)
    if not user or not is_platform_admin(db, user):
        query = query.where(or_((Product.status == 'active') & (Merchant.status == 'active'), Product.merchant_id.in_(owned_merchant_ids(user))))
    return list(db.scalars(query.order_by(Product.id).offset(offset).limit(limit)))

@router.get("/products/{item_id}", summary="查询商品详情", response_model=schema.ProductRead)
def get_product(item_id: int, db: Session = Depends(get_db), user = Depends(optional_user)):
    """按 ID 获取商品详情。"""
    item = service.require(db, Product, item_id)
    merchant = service.require(db, Merchant, item.merchant_id)
    if (item.status != 'active' or merchant.status != 'active') and not (user and is_platform_admin(db, user)):
        if user is None: raise HTTPException(404, '资源不存在')
        require_merchant(db, user, item.merchant_id, admin=False)
    return item

@router.patch("/products/{item_id}", summary="修改商品", response_model=schema.ProductRead)
def update_product(item_id: int, data: schema.ProductUpdate, db: Session = Depends(get_db), user = Depends(current_user)):
    """按 ID 部分更新商品信息。"""
    require_merchant(db, user, service.require(db, Product, item_id).merchant_id)
    return service.update_item(db, Product, item_id, data)

@router.delete("/products/{item_id}", summary="删除商品", status_code=204)
def delete_product(item_id: int, db: Session = Depends(get_db), user = Depends(current_user)):
    """检查商品存在后删除商品。"""
    require_merchant(db, user, service.require(db, Product, item_id).merchant_id)
    service.delete_product(db, item_id)
    return Response(status_code=204)
