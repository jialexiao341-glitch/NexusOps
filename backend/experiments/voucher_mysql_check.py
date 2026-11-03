"""在临时 MySQL 数据库验证迁移和抢购；不操作现有开发库的数据。"""
import os
import re
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from alembic import command
from alembic.config import Config
from fastapi import HTTPException
from sqlalchemy import create_engine, select, func, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from app.core.config import settings
from app.merchant.model import Merchant, User, VoucherCampaign, VoucherOrder, utcnow
from app.merchant.vouchers import OrderRequest, create_order

def main():
    url=make_url(settings.database_url)
    if os.environ.get('NEXUSOPS_ENV') != 'test' or url.host not in ('127.0.0.1','localhost') or url.database != 'nexusops_test':
        raise SystemExit('须明确选择本机 nexusops_test 配置')
    name='nexusops_voucher_check_'+uuid.uuid4().hex[:12]
    assert re.fullmatch(r'nexusops_voucher_check_[0-9a-f]{12}',name)
    admin=create_engine(url._replace(database=None),isolation_level='AUTOCOMMIT')
    created=False
    engine=None
    try:
        with admin.connect() as c: c.execute(text(f'CREATE DATABASE `{name}` CHARACTER SET utf8mb4'))
        created=True
        target=url.set(database=name)
        settings.database_url=target.render_as_string(hide_password=False)
        command.upgrade(Config('alembic.ini'),'head')
        engine=create_engine(target,pool_size=30,max_overflow=0)
        with Session(engine) as db:
            merchant=Merchant(name='test',status='active');db.add(merchant)
            users=[User(username=f'u{i}',mobile=f'139{i:08d}',password_hash='x',status='active') for i in range(30)]
            db.add_all(users);db.flush()
            now=utcnow()
            campaign=VoucherCampaign(merchant_id=merchant.id,title='test',sale_price=Decimal('9.00'),total_stock=10,available_stock=10,starts_at=now-timedelta(minutes=1),ends_at=now+timedelta(hours=1),status='active')
            db.add(campaign);db.commit()
            cid=campaign.id; mid=merchant.id; ids=[u.id for u in users]
        barrier=threading.Barrier(len(ids))
        def attempt(uid):
            with Session(engine,expire_on_commit=False) as db:
                user=db.get(User,uid)
                barrier.wait()
                try:
                    return create_order(cid,OrderRequest(request_id=f'req_{uid}'),db,user).id
                except HTTPException as error:
                    if error.status_code!=409: raise
                    return None
        with ThreadPoolExecutor(max_workers=len(ids)) as pool:
            results=list(pool.map(attempt,ids))
        with Session(engine) as db:
            orders=db.scalar(select(func.count()).select_from(VoucherOrder))
            stock=db.get(VoucherCampaign,cid).available_stock
        success=sum(value is not None for value in results)
        print(f'requests={len(ids)} success={success} orders={orders} remaining={stock}')
        if (success,orders,stock)!=(10,10,0): raise RuntimeError('并发结果不符合预期')
        with Session(engine) as db:
            now=utcnow()
            retry_campaign=VoucherCampaign(merchant_id=mid,title='retry',sale_price=Decimal('9.00'),total_stock=10,available_stock=10,starts_at=now-timedelta(minutes=1),ends_at=now+timedelta(hours=1),status='active')
            db.add(retry_campaign);db.commit();retry_id=retry_campaign.id
        barrier=threading.Barrier(12)
        def retry(_):
            with Session(engine,expire_on_commit=False) as db:
                user=db.get(User,ids[0]);barrier.wait()
                return create_order(retry_id,OrderRequest(request_id='same_request'),db,user).id
        with ThreadPoolExecutor(max_workers=12) as pool:
            retries=list(pool.map(retry,range(12)))
        with Session(engine) as db:
            retry_orders=db.scalar(select(func.count()).select_from(VoucherOrder).where(VoucherOrder.campaign_id==retry_id))
            retry_stock=db.get(VoucherCampaign,retry_id).available_stock
        print(f'retries=12 distinct_order_ids={len(set(retries))} orders={retry_orders} remaining={retry_stock}')
        if (len(set(retries)),retry_orders,retry_stock)!=(1,1,9): raise RuntimeError('重复请求未正确合并')
    finally:
        if engine is not None: engine.dispose()
        if created:
            with admin.connect() as c: c.execute(text(f'DROP DATABASE `{name}`'))
        admin.dispose()

if __name__=='__main__': main()
