"""优惠券活动和同步订单：库存、限购与幂等由数据库事务保证。"""
from datetime import datetime, timezone
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_serializer, model_validator
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.identity.controller import current_user, optional_user
from app.identity.permissions import is_platform_admin, owned_merchant_ids, require_merchant
from app.merchant.model import Merchant, VoucherCampaign, VoucherOrder, utcnow
from app.merchant.service import require

router = APIRouter(prefix='/api/v1', tags=['优惠券'])

class CampaignCreate(BaseModel):
    merchant_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=120)
    sale_price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    total_stock: int = Field(ge=0)
    starts_at: AwareDatetime
    ends_at: AwareDatetime

    @model_validator(mode='after')
    def check_time(self):
        if self.starts_at >= self.ends_at: raise ValueError('活动结束时间须晚于开始时间')
        return self

class CampaignRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    merchant_id: int
    title: str
    sale_price: Decimal
    total_stock: int
    available_stock: int
    starts_at: datetime
    ends_at: datetime
    status: str

    @field_serializer('starts_at', 'ends_at')
    def serialize_utc(self, value: datetime):
        return value.replace(tzinfo=timezone.utc).isoformat()

class OrderRequest(BaseModel):
    request_id: str = Field(min_length=1, max_length=64, pattern=r'^[A-Za-z0-9_-]+$')

class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    campaign_id: int
    user_id: int
    request_id: str
    amount_snapshot: Decimal
    status: str

@router.post('/voucher-campaigns', response_model=CampaignRead, status_code=201)
def create_campaign(data: CampaignCreate, db: Session = Depends(get_db), user = Depends(current_user)):
    require(db, Merchant, data.merchant_id)
    require_merchant(db, user, data.merchant_id)
    values=data.model_dump()
    for field in ('starts_at','ends_at'): values[field]=values[field].astimezone(timezone.utc).replace(tzinfo=None)
    item=VoucherCampaign(**values, available_stock=data.total_stock, status='draft')
    db.add(item); db.commit(); db.refresh(item)
    return item

@router.get('/voucher-campaigns/{campaign_id}', response_model=CampaignRead)
def campaign_detail(campaign_id:int, db:Session=Depends(get_db), user=Depends(optional_user)):
    item=require(db,VoucherCampaign,campaign_id)
    merchant=require(db,Merchant,item.merchant_id)
    if item.status != 'active' or merchant.status != 'active':
        if user is None: raise HTTPException(404,'资源不存在')
        require_merchant(db,user,item.merchant_id,admin=False)
    return item

@router.get('/voucher-campaigns', response_model=list[CampaignRead])
def list_campaigns(merchant_id:int|None=Query(None,gt=0), offset:int=Query(0,ge=0), limit:int=Query(20,ge=1,le=100), db:Session=Depends(get_db), user=Depends(optional_user)):
    from sqlalchemy import or_
    query=select(VoucherCampaign).join(Merchant,Merchant.id==VoucherCampaign.merchant_id)
    if not user or not is_platform_admin(db,user):
        query=query.where(or_((VoucherCampaign.status=='active') & (Merchant.status=='active'),VoucherCampaign.merchant_id.in_(owned_merchant_ids(user))))
    if merchant_id is not None: query=query.where(VoucherCampaign.merchant_id==merchant_id)
    return list(db.scalars(query.order_by(VoucherCampaign.id).offset(offset).limit(limit)))

@router.post('/voucher-campaigns/{campaign_id}/activate', response_model=CampaignRead)
def activate_campaign(campaign_id:int, db:Session=Depends(get_db), user=Depends(current_user)):
    item=require(db,VoucherCampaign,campaign_id); require_merchant(db,user,item.merchant_id)
    result=db.execute(update(VoucherCampaign).where(VoucherCampaign.id==campaign_id,VoucherCampaign.status=='draft').values(status='active'))
    if not result.rowcount: raise HTTPException(409,'只有草稿活动可以上线')
    db.commit(); db.refresh(item); return item

@router.post('/voucher-campaigns/{campaign_id}/close', response_model=CampaignRead)
def close_campaign(campaign_id:int, db:Session=Depends(get_db), user=Depends(current_user)):
    item=require(db,VoucherCampaign,campaign_id); require_merchant(db,user,item.merchant_id)
    result=db.execute(update(VoucherCampaign).where(VoucherCampaign.id==campaign_id,VoucherCampaign.status.in_(['draft','active'])).values(status='closed'))
    if not result.rowcount: raise HTTPException(409,'活动已关闭')
    db.commit(); db.refresh(item); return item

def prior_request(db, user_id, request_id, campaign_id):
    item=db.scalar(select(VoucherOrder).where(VoucherOrder.user_id==user_id,VoucherOrder.request_id==request_id))
    if item is not None and item.campaign_id != campaign_id: raise HTTPException(409,'请求标识已用于其他活动')
    return item

@router.post('/voucher-campaigns/{campaign_id}/orders', response_model=OrderRead, status_code=201)
def create_order(campaign_id:int, data:OrderRequest, db:Session=Depends(get_db), user=Depends(current_user)):
    previous=prior_request(db,user.id,data.request_id,campaign_id)
    if previous: return previous
    now=utcnow()
    try:
        result=db.execute(update(VoucherCampaign).where(VoucherCampaign.id==campaign_id,VoucherCampaign.status=='active',VoucherCampaign.starts_at<=now,VoucherCampaign.ends_at>now,VoucherCampaign.available_stock>0,VoucherCampaign.merchant_id.in_(select(Merchant.id).where(Merchant.status=='active'))).values(available_stock=VoucherCampaign.available_stock-1))
        if not result.rowcount:
            db.rollback()
            previous=prior_request(db,user.id,data.request_id,campaign_id)
            if previous: return previous
            raise HTTPException(409,'活动不可购买或库存不足')
        campaign=require(db,VoucherCampaign,campaign_id)
        order=VoucherOrder(campaign_id=campaign_id,user_id=user.id,request_id=data.request_id,amount_snapshot=campaign.sale_price,status='created',active_marker=1)
        db.add(order); db.commit(); db.refresh(order); return order
    except IntegrityError:
        db.rollback()
        previous=prior_request(db,user.id,data.request_id,campaign_id)
        if previous: return previous
        raise HTTPException(409,'已有有效订单')

@router.get('/voucher-orders/{order_id}', response_model=OrderRead)
def order_detail(order_id:int, db:Session=Depends(get_db), user=Depends(current_user)):
    item=db.scalar(select(VoucherOrder).where(VoucherOrder.id==order_id,VoucherOrder.user_id==user.id))
    if item is None: raise HTTPException(404,'资源不存在')
    return item

@router.post('/voucher-orders/{order_id}/cancel', response_model=OrderRead)
def cancel_order(order_id:int, db:Session=Depends(get_db), user=Depends(current_user)):
    item=db.scalar(select(VoucherOrder).where(VoucherOrder.id==order_id,VoucherOrder.user_id==user.id))
    if item is None: raise HTTPException(404,'资源不存在')
    db.execute(select(VoucherCampaign.id).where(VoucherCampaign.id==item.campaign_id).with_for_update()).scalar_one()
    item=db.scalar(select(VoucherOrder).where(VoucherOrder.id==order_id,VoucherOrder.user_id==user.id).with_for_update().execution_options(populate_existing=True))
    result=db.execute(update(VoucherOrder).where(VoucherOrder.id==order_id,VoucherOrder.user_id==user.id,VoucherOrder.status=='created').values(status='cancelled',active_marker=None))
    if result.rowcount:
        db.execute(update(VoucherCampaign).where(VoucherCampaign.id==item.campaign_id).values(available_stock=VoucherCampaign.available_stock+1))
    else:
        db.refresh(item)
        if item.status!='cancelled': raise HTTPException(409,'当前订单不能取消')
    db.commit(); db.refresh(item); return item
