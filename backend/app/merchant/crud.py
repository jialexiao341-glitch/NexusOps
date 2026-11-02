"""商户与商品的数据访问操作。"""
from sqlalchemy import select
from sqlalchemy.orm import Session

def get(db: Session, model, item_id: int):
    """按主键查询指定模型，未找到时返回 None。"""
    return db.get(model, item_id)

def list_items(db: Session, model, offset: int, limit: int):
    """按主键顺序分页查询指定模型。"""
    return list(db.scalars(select(model).order_by(model.id).offset(offset).limit(limit)))

def create(db: Session, model, values: dict):
    """根据字段创建记录并提交事务。"""
    item = model(**values)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

def update(db: Session, item, values: dict):
    """更新指定记录的字段并提交事务。"""
    for key, value in values.items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item

def delete(db: Session, item):
    """删除指定记录并提交事务。"""
    db.delete(item)
    db.commit()
