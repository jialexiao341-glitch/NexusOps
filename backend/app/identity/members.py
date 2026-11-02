"""商户成员管理和当前用户权限。"""
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.identity.controller import current_user
from app.identity import schema, service
from app.identity.permissions import require_merchant, require_platform_admin
from app.merchant.model import Merchant, MerchantMembership, User, UserPlatformRole

router = APIRouter(prefix='/api/v1', tags=['角色与商户成员'])
Role = Literal['admin', 'staff']

class MemberCreate(BaseModel):
    user_id: int = Field(gt=0)
    role: Role

class MemberUpdate(BaseModel):
    role: Role

class MemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    merchant_id: int
    user_id: int
    role: Role
    status: str

def locked_merchant(db, merchant_id):
    merchant = db.scalar(select(Merchant).where(Merchant.id == merchant_id).with_for_update())
    if merchant is None:
        raise HTTPException(404, '商户不存在')
    return merchant

def get_member(db, merchant_id, user_id):
    member = db.scalar(select(MerchantMembership).where(MerchantMembership.merchant_id == merchant_id, MerchantMembership.user_id == user_id))
    if member is None:
        raise HTTPException(404, '成员不存在')
    return member

def protect_last_admin(db, member):
    if member.role == 'admin' and member.status == 'active':
        count = db.scalar(select(func.count()).select_from(MerchantMembership).where(MerchantMembership.merchant_id == member.merchant_id, MerchantMembership.role == 'admin', MerchantMembership.status == 'active'))
        if count <= 1:
            raise HTTPException(409, '商户必须保留至少一名管理员')

@router.get('/users/me/permissions')
def my_permissions(user=Depends(current_user), db: Session = Depends(get_db)):
    roles = list(db.scalars(select(UserPlatformRole.role).where(UserPlatformRole.user_id == user.id)))
    members = list(db.scalars(select(MerchantMembership).where(MerchantMembership.user_id == user.id, MerchantMembership.status == 'active')))
    return {'platform_roles': roles, 'memberships': [MemberRead.model_validate(item) for item in members]}

@router.get('/admin/users')
def list_users(response: Response, offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100), keyword: str = Query('', max_length=100), status: Literal['active', 'inactive'] | None = None, user=Depends(current_user), db: Session = Depends(get_db)):
    require_platform_admin(db, user)
    query = select(User)
    if keyword.strip():
        query = query.where(or_(User.username.contains(keyword.strip(), autoescape=True), User.nickname.contains(keyword.strip(), autoescape=True)))
    if status:
        query = query.where(User.status == status)
    response.headers['X-Total-Count'] = str(db.scalar(select(func.count()).select_from(query.subquery())))
    users = list(db.scalars(query.order_by(User.id).offset(offset).limit(limit)))
    ids = [item.id for item in users]
    admins = set(db.scalars(select(UserPlatformRole.user_id).where(UserPlatformRole.user_id.in_(ids), UserPlatformRole.role == 'platform_admin')))
    supers = set(db.scalars(select(UserPlatformRole.user_id).where(UserPlatformRole.user_id.in_(ids), UserPlatformRole.role == 'super_admin')))
    return [{'id': item.id, 'username': item.username, 'nickname': item.nickname, 'mobile': item.mobile, 'created_at': item.created_at, 'status': item.status, 'platform_admin': item.id in admins, 'super_admin': item.id in supers} for item in users]

@router.post('/admin/users', response_model=schema.UserRead, status_code=201)
def create_user(data: schema.AdminUserCreate, user=Depends(current_user), db: Session = Depends(get_db)):
    require_platform_admin(db, user)
    item = User(username=data.username, mobile=data.mobile, nickname=data.nickname, password_hash=service.hash_password(data.password), mobile_verified_at=None, status='active')
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, '手机号或账号已存在')
    db.refresh(item)
    return item

def lock_platform_admins(db):
    return list(db.scalars(select(UserPlatformRole).where(UserPlatformRole.role == 'platform_admin').order_by(UserPlatformRole.id).with_for_update()))

@router.put('/admin/users/{user_id}/platform-admin', status_code=204)
def grant_platform_admin(user_id: int, user=Depends(current_user), db: Session = Depends(get_db)):
    admins = lock_platform_admins(db)
    if not any(item.user_id == user.id for item in admins):
        raise HTTPException(403, '需要平台管理员权限')
    target = db.get(User, user_id)
    if target is None or target.status != 'active':
        raise HTTPException(404, '有效用户不存在')
    if not any(item.user_id == user_id for item in admins):
        db.add(UserPlatformRole(user_id=user_id, role='platform_admin'))
        db.commit()
    return Response(status_code=204)

@router.delete('/admin/users/{user_id}/platform-admin', status_code=204)
def revoke_platform_admin(user_id: int, user=Depends(current_user), db: Session = Depends(get_db)):
    admins = lock_platform_admins(db)
    if not any(item.user_id == user.id for item in admins):
        raise HTTPException(403, '需要平台管理员权限')
    target = next((item for item in admins if item.user_id == user_id), None)
    if target is None:
        raise HTTPException(404, '用户不是平台管理员')
    if db.scalar(select(UserPlatformRole.id).where(UserPlatformRole.user_id == user_id, UserPlatformRole.role == 'super_admin')) is not None:
        raise HTTPException(409, '超级管理员权限不可撤销')
    active_admins = db.scalar(select(func.count()).select_from(User).where(User.status == 'active', User.id.in_([item.user_id for item in admins])))
    target_user = db.get(User, user_id)
    if target_user and target_user.status == 'active' and active_admins <= 1:
        raise HTTPException(409, '必须保留至少一名平台管理员')
    db.delete(target); db.commit()
    return Response(status_code=204)

@router.get('/merchants/{merchant_id}/members', response_model=list[MemberRead])
def list_members(merchant_id: int, user=Depends(current_user), db: Session = Depends(get_db)):
    require_merchant(db, user, merchant_id, platform=True)
    return list(db.scalars(select(MerchantMembership).where(MerchantMembership.merchant_id == merchant_id).order_by(MerchantMembership.id)))

@router.post('/merchants/{merchant_id}/members', response_model=MemberRead, status_code=201)
def add_member(merchant_id: int, data: MemberCreate, user=Depends(current_user), db: Session = Depends(get_db)):
    locked_merchant(db, merchant_id)
    require_merchant(db, user, merchant_id, platform=True)
    target = db.get(User, data.user_id)
    if target is None or target.status != 'active':
        raise HTTPException(404, '有效用户不存在')
    member = MerchantMembership(merchant_id=merchant_id, user_id=data.user_id, role=data.role, status='active')
    db.add(member)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, '用户已是商户成员')
    db.refresh(member)
    return member

@router.patch('/merchants/{merchant_id}/members/{user_id}', response_model=MemberRead)
def update_member(merchant_id: int, user_id: int, data: MemberUpdate, user=Depends(current_user), db: Session = Depends(get_db)):
    locked_merchant(db, merchant_id)
    require_merchant(db, user, merchant_id, platform=True)
    member = get_member(db, merchant_id, user_id)
    if data.role != 'admin': protect_last_admin(db, member)
    member.role = data.role
    db.commit(); db.refresh(member)
    return member

@router.delete('/merchants/{merchant_id}/members/{user_id}', status_code=204)
def delete_member(merchant_id: int, user_id: int, user=Depends(current_user), db: Session = Depends(get_db)):
    locked_merchant(db, merchant_id)
    require_merchant(db, user, merchant_id, platform=True)
    member = get_member(db, merchant_id, user_id)
    protect_last_admin(db, member)
    db.delete(member); db.commit()
    return Response(status_code=204)
