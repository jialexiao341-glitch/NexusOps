"""平台角色与商户成员权限检查。"""
from fastapi import HTTPException
from sqlalchemy import false, select
from app.merchant.model import MerchantMembership, UserPlatformRole


def is_platform_admin(db, user):
    return db.scalar(select(UserPlatformRole.id).where(UserPlatformRole.user_id == user.id, UserPlatformRole.role == 'platform_admin')) is not None


def require_platform_admin(db, user):
    if not is_platform_admin(db, user):
        raise HTTPException(403, '需要平台管理员权限')


def require_merchant(db, user, merchant_id, *, admin=True, platform=True):
    if platform and is_platform_admin(db, user):
        return
    roles = ('admin',) if admin else ('admin', 'staff')
    membership = db.scalar(select(MerchantMembership.id).where(
        MerchantMembership.merchant_id == merchant_id,
        MerchantMembership.user_id == user.id,
        MerchantMembership.status == 'active',
        MerchantMembership.role.in_(roles),
    ))
    if membership is None:
        raise HTTPException(403, '无权访问该商户')


def owned_merchant_ids(user):
    if user is None:
        return select(MerchantMembership.merchant_id).where(false())
    return select(MerchantMembership.merchant_id).where(MerchantMembership.user_id == user.id, MerchantMembership.status == 'active', MerchantMembership.role.in_(('admin', 'staff')))
