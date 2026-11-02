"""分类、商品规格及库存接口。"""
from decimal import Decimal
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.merchant.model import Merchant, Product, ProductCategory, ProductSku, Inventory
from app.merchant.service import require

router = APIRouter(prefix='/api/v1', tags=['分类、规格与库存'])
Status = Literal['active', 'inactive']

class CategoryCreate(BaseModel):
    merchant_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=120)
    sort_order: int = 0
    status: Status = 'active'

class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    sort_order: int | None = None
    status: Status | None = None

class CategoryRead(CategoryCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int

class SkuCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    status: Status = 'active'

class SkuUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    price: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    status: Status | None = None

class SkuRead(SkuCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int

class InventoryUpdate(BaseModel):
    available: int = Field(ge=0)

class InventoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    sku_id: int
    available: int
    reserved: int
    version: int

def commit(db):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, '数据冲突或存在关联记录')

def apply(item, data):
    values = data.model_dump(exclude_unset=True)
    if any(v is None for v in values.values()):
        raise HTTPException(422, '字段不能为 null')
    for key, value in values.items():
        setattr(item, key, value)

@router.post('/categories', response_model=CategoryRead, status_code=201)
def create_category(data: CategoryCreate, db: Session = Depends(get_db)):
    require(db, Merchant, data.merchant_id)
    item = ProductCategory(**data.model_dump())
    db.add(item); commit(db); db.refresh(item)
    return item

@router.get('/categories', response_model=list[CategoryRead])
def categories(merchant_id: int | None = Query(None, gt=0), offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    query = select(ProductCategory)
    if merchant_id is not None: query = query.where(ProductCategory.merchant_id == merchant_id)
    return list(db.scalars(query.order_by(ProductCategory.id).offset(offset).limit(limit)))

@router.get('/categories/{item_id}', response_model=CategoryRead)
def category(item_id: int, db: Session = Depends(get_db)):
    return require(db, ProductCategory, item_id)

@router.patch('/categories/{item_id}', response_model=CategoryRead)
def update_category(item_id: int, data: CategoryUpdate, db: Session = Depends(get_db)):
    item = require(db, ProductCategory, item_id); apply(item, data); commit(db); db.refresh(item)
    return item

@router.delete('/categories/{item_id}', status_code=204)
def delete_category(item_id: int, db: Session = Depends(get_db)):
    item = require(db, ProductCategory, item_id)
    if db.scalar(select(Product.id).where(Product.category_id == item_id).limit(1)) is not None:
        raise HTTPException(409, '分类下存在商品，不能删除')
    db.delete(item); commit(db)
    return Response(status_code=204)

@router.post('/products/{product_id}/skus', response_model=SkuRead, status_code=201)
def create_sku(product_id: int, data: SkuCreate, db: Session = Depends(get_db)):
    require(db, Product, product_id)
    item = ProductSku(product_id=product_id, **data.model_dump(), inventory=Inventory())
    db.add(item); commit(db); db.refresh(item)
    return item

@router.get('/products/{product_id}/skus', response_model=list[SkuRead])
def skus(product_id: int, db: Session = Depends(get_db)):
    require(db, Product, product_id)
    return list(db.scalars(select(ProductSku).where(ProductSku.product_id == product_id).order_by(ProductSku.id)))

@router.get('/skus/{item_id}', response_model=SkuRead)
def sku(item_id: int, db: Session = Depends(get_db)):
    return require(db, ProductSku, item_id)

@router.patch('/skus/{item_id}', response_model=SkuRead)
def update_sku(item_id: int, data: SkuUpdate, db: Session = Depends(get_db)):
    item = require(db, ProductSku, item_id); apply(item, data); commit(db); db.refresh(item)
    return item

@router.delete('/skus/{item_id}', status_code=204)
def delete_sku(item_id: int, db: Session = Depends(get_db)):
    item = require(db, ProductSku, item_id)
    first = db.scalar(select(ProductSku.id).where(ProductSku.product_id == item.product_id).order_by(ProductSku.id).limit(1))
    if item.id == first: raise HTTPException(409, '默认规格不能单独删除')
    if item.inventory and item.inventory.reserved: raise HTTPException(409, '规格存在预留库存，不能删除')
    db.delete(item); commit(db)
    return Response(status_code=204)

@router.get('/skus/{item_id}/inventory', response_model=InventoryRead)
def inventory(item_id: int, db: Session = Depends(get_db)):
    require(db, ProductSku, item_id)
    return require(db, Inventory, item_id)

@router.put('/skus/{item_id}/inventory', response_model=InventoryRead)
def update_inventory(item_id: int, data: InventoryUpdate, db: Session = Depends(get_db)):
    require(db, ProductSku, item_id)
    item = require(db, Inventory, item_id)
    db.execute(update(Inventory).where(Inventory.sku_id == item_id).values(available=data.available, version=Inventory.version + 1))
    commit(db); db.refresh(item)
    return item
