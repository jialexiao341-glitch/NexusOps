"""商户与商品业务服务：校验业务规则并协调数据访问。"""
from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from app.merchant import crud
from app.merchant.model import Inventory, Merchant, MerchantMembership, Product, ProductSku, ProductCategory

def require(db: Session, model, item_id: int):
    """按主键查找记录；不存在时返回 404。"""
    item = crud.get(db, model, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="资源不存在")
    return item

def check_category(db, merchant_id, category_id):
    if category_id is not None:
        category = require(db, ProductCategory, category_id)
        if category.merchant_id != merchant_id:
            raise HTTPException(422, "分类与商品必须属于同一商户")

def create_product(db: Session, data):
    """检查所属商户存在后创建商品。"""
    require(db, Merchant, data.merchant_id)
    values = data.model_dump()
    check_category(db, data.merchant_id, values.get("category_id"))
    price = values.pop("price")
    product = Product(**values)
    product.skus.append(ProductSku(name="默认规格", price=price, inventory=Inventory()))
    db.add(product)
    db.commit()
    db.refresh(product)
    return product

def update_item(db: Session, model, item_id: int, data):
    """校验更新字段后修改指定记录。"""
    values = data.model_dump(exclude_unset=True)
    if any(value is None and not (model is Product and key == "category_id") for key, value in values.items()):
        raise HTTPException(status_code=422, detail="字段不能为 null")
    item = require(db, model, item_id)
    if model is Product and "category_id" in values:
        check_category(db, item.merchant_id, values["category_id"])
    if model is Product and "price" in values:
        item.skus[0].price = values.pop("price")
    return crud.update(db, item, values)

def delete_merchant(db: Session, item_id: int):
    """商户存在关联商品时拒绝删除，否则删除商户。"""
    item = require(db, Merchant, item_id)
    if db.scalar(select(ProductCategory.id).where(ProductCategory.merchant_id == item_id).limit(1)) is not None:
        raise HTTPException(status_code=409, detail="商户存在分类，不能删除")
    if db.scalar(select(Product.id).where(Product.merchant_id == item_id).limit(1)) is not None:
        raise HTTPException(status_code=409, detail="商户存在商品，不能删除")
    db.execute(delete(MerchantMembership).where(MerchantMembership.merchant_id == item_id))
    crud.delete(db, item)


def list_items(db: Session, model, offset: int, limit: int):
    """按主键顺序分页查询指定模型。"""
    return crud.list_items(db, model, offset, limit)

def create_merchant(db: Session, data):
    """创建一条商户记录。"""
    return crud.create(db, Merchant, data.model_dump())

def delete_product(db: Session, item_id: int):
    """检查商品存在后删除商品。"""
    item = require(db, Product, item_id)
    if any(sku.inventory and sku.inventory.reserved for sku in item.skus):
        raise HTTPException(409, "商品存在预留库存，不能删除")
    crud.delete(db, item)

