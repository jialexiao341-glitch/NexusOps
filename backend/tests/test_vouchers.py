from datetime import datetime, timedelta, timezone
from test_crud import client, business_client

def test_campaign_order_cancel_rebuy_idempotency(business_client):
    client=business_client
    mid=client.post('/api/v1/merchants',json={'name':'Shop'}).json()['id']
    now=datetime.now(timezone.utc)
    payload={'merchant_id':mid,'title':'Deal','sale_price':'9.90','total_stock':1,'starts_at':(now-timedelta(minutes=1)).isoformat(),'ends_at':(now+timedelta(hours=1)).isoformat()}
    campaign=client.post('/api/v1/voucher-campaigns',json=payload)
    assert campaign.status_code==201
    assert client.delete(f'/api/v1/merchants/{mid}').status_code==409
    cid=campaign.json()['id']
    assert client.post(f'/api/v1/voucher-campaigns/{cid}/activate').status_code==200
    first=client.post(f'/api/v1/voucher-campaigns/{cid}/orders',json={'request_id':'first'})
    assert first.status_code==201
    oid=first.json()['id']
    assert client.post(f'/api/v1/voucher-campaigns/{cid}/orders',json={'request_id':'first'}).json()['id']==oid
    assert client.post(f'/api/v1/voucher-campaigns/{cid}/orders',json={'request_id':'second'}).status_code==409
    assert client.post(f'/api/v1/voucher-orders/{oid}/cancel').json()['status']=='cancelled'
    assert client.post(f'/api/v1/voucher-orders/{oid}/cancel').json()['status']=='cancelled'
    assert client.post(f'/api/v1/voucher-campaigns/{cid}/orders',json={'request_id':'first'}).json()['id']==oid
    second=client.post(f'/api/v1/voucher-campaigns/{cid}/orders',json={'request_id':'second'})
    assert second.status_code==201 and second.json()['id'] != oid
    assert client.get(f'/api/v1/voucher-campaigns/{cid}').json()['available_stock']==0

def test_campaign_authorization_and_window(business_client):
    from app.core.database import get_db
    from app.main import app
    from app.identity.service import tokens
    from app.merchant.model import User
    client=business_client
    mid=client.post('/api/v1/merchants',json={'name':'Shop'}).json()['id']
    with next(app.dependency_overrides[get_db]()) as db:
        other=User(username='buyer',mobile='13300000000',password_hash='x',status='active')
        db.add(other);db.commit();other_header={'Authorization':'Bearer '+tokens(other)['access_token']}
    now=datetime.now(timezone.utc)
    base={'merchant_id':mid,'title':'Deal','sale_price':'9','total_stock':1,'starts_at':(now+timedelta(hours=1)).isoformat(),'ends_at':(now+timedelta(hours=2)).isoformat()}
    assert client.post('/api/v1/voucher-campaigns',headers=other_header,json=base).status_code==403
    assert client.post('/api/v1/voucher-campaigns',json={**base,'starts_at':'2026-01-01T00:00:00'}).status_code==422
    assert client.post('/api/v1/voucher-campaigns',json={**base,'ends_at':base['starts_at']}).status_code==422
    cid=client.post('/api/v1/voucher-campaigns',json=base).json()['id']
    assert client.post(f'/api/v1/voucher-campaigns/{cid}/activate',headers=other_header).status_code==403
    assert client.post(f'/api/v1/voucher-campaigns/{cid}/activate').status_code==200
    assert client.post(f'/api/v1/voucher-campaigns/{cid}/orders',json={'request_id':'future'}).status_code==409
    assert client.post(f'/api/v1/voucher-campaigns/{cid}/close').status_code==200
    assert client.post(f'/api/v1/voucher-campaigns/{cid}/activate').status_code==409


def test_different_request_same_user_does_not_consume_stock(business_client):
    client=business_client
    mid=client.post('/api/v1/merchants',json={'name':'Shop'}).json()['id']
    now=datetime.now(timezone.utc)
    body={'merchant_id':mid,'title':'Deal','sale_price':'9','total_stock':3,'starts_at':(now-timedelta(minutes=1)).isoformat(),'ends_at':(now+timedelta(hours=1)).isoformat()}
    cid=client.post('/api/v1/voucher-campaigns',json=body).json()['id']
    client.post(f'/api/v1/voucher-campaigns/{cid}/activate')
    assert client.post(f'/api/v1/voucher-campaigns/{cid}/orders',json={'request_id':'a'}).status_code==201
    assert client.post(f'/api/v1/voucher-campaigns/{cid}/orders',json={'request_id':'b'}).status_code==409
    assert client.get(f'/api/v1/voucher-campaigns/{cid}').json()['available_stock']==2

def test_order_access_and_request_id_scope(business_client):
    from app.core.database import get_db
    from app.main import app
    from app.identity.service import tokens
    from app.merchant.model import User
    client=business_client
    mid=client.post('/api/v1/merchants',json={'name':'Shop'}).json()['id']
    with next(app.dependency_overrides[get_db]()) as db:
        user=User(username='stranger',mobile='13200000000',password_hash='x',status='active')
        db.add(user);db.commit();headers={'Authorization':'Bearer '+tokens(user)['access_token']}
    now=datetime.now(timezone.utc)
    data={'merchant_id':mid,'title':'Deal','sale_price':'1','total_stock':2,'starts_at':(now-timedelta(seconds=10)).isoformat(),'ends_at':(now+timedelta(hours=1)).isoformat()}
    one=client.post('/api/v1/voucher-campaigns',json=data).json()['id']
    two=client.post('/api/v1/voucher-campaigns',json=data).json()['id']
    for cid in (one,two): client.post(f'/api/v1/voucher-campaigns/{cid}/activate')
    order=client.post(f'/api/v1/voucher-campaigns/{one}/orders',json={'request_id':'same'}).json()
    assert client.post(f'/api/v1/voucher-campaigns/{two}/orders',json={'request_id':'same'}).status_code==409
    assert client.get(f"/api/v1/voucher-orders/{order['id']}",headers=headers).status_code==404
    assert client.post(f"/api/v1/voucher-orders/{order['id']}/cancel",headers=headers).status_code==404
    assert client.get(f'/api/v1/voucher-campaigns/{one}').json()['available_stock']==1
