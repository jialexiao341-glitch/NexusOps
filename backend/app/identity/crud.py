"""用户身份数据访问。"""
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.merchant.model import User

def by_mobile(db: Session, mobile: str):
    """按手机号查询用户。"""
    return db.scalar(select(User).where(User.mobile == mobile))
def by_username(db: Session, username: str):
    """按登录账号查询用户。"""
    return db.scalar(select(User).where(User.username == username))
