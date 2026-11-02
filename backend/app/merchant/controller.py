"""商户与商品 HTTP 接口。"""
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.merchant import schema, service
from app.merchant.model import Merchant, Product

router = APIRouter(prefix="/api/v1", tags=["商户与商品"])

@router.post("/merchants", summary="创建商户", response_model=schema.MerchantRead, status_code=201)
def create_merchant(data: schema.MerchantCreate, db: Session = Depends(get_db)):
    """创建一条商户记录。"""
    return service.create_merchant(db, data)

@router.get("/merchants", summary="分页查询商户", response_model=list[schema.MerchantRead])
def list_merchants(offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    """分页返回商户列表。"""
    return service.list_items(db, Merchant, offset, limit)

@router.get("/merchants/{item_id}", summary="查询商户详情", response_model=schema.MerchantRead)
def get_merchant(item_id: int, db: Session = Depends(get_db)):
    """按 ID 获取商户详情。"""
    return service.require(db, Merchant, item_id)

@router.patch("/merchants/{item_id}", summary="修改商户", response_model=schema.MerchantRead)
def update_merchant(item_id: int, data: schema.MerchantUpdate, db: Session = Depends(get_db)):
    """按 ID 部分更新商户信息。"""
    return service.update_item(db, Merchant, item_id, data)

@router.delete("/merchants/{item_id}", summary="删除商户", status_code=204)
def delete_merchant(item_id: int, db: Session = Depends(get_db)):
    """商户存在关联商品时拒绝删除，否则删除商户。"""
    service.delete_merchant(db, item_id)
    return Response(status_code=204)

@router.post("/products", summary="创建商品", response_model=schema.ProductRead, status_code=201)
def create_product(data: schema.ProductCreate, db: Session = Depends(get_db)):
    """检查所属商户存在后创建商品。"""
    return service.create_product(db, data)

@router.get("/products", summary="分页查询商品", response_model=list[schema.ProductRead])
def list_products(offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    """分页返回商品列表。"""
    return service.list_items(db, Product, offset, limit)

@router.get("/products/{item_id}", summary="查询商品详情", response_model=schema.ProductRead)
def get_product(item_id: int, db: Session = Depends(get_db)):
    """按 ID 获取商品详情。"""
    return service.require(db, Product, item_id)

@router.patch("/products/{item_id}", summary="修改商品", response_model=schema.ProductRead)
def update_product(item_id: int, data: schema.ProductUpdate, db: Session = Depends(get_db)):
    """按 ID 部分更新商品信息。"""
    return service.update_item(db, Product, item_id, data)

@router.delete("/products/{item_id}", summary="删除商品", status_code=204)
def delete_product(item_id: int, db: Session = Depends(get_db)):
    """检查商品存在后删除商品。"""
    service.delete_product(db, item_id)
    return Response(status_code=204)
