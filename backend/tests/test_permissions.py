from datetime import datetime, timezone
import pytest
from test_crud import client
from app.core.database import get_db
from app.main import app
from app.identity.service import tokens
from app.merchant.model import User, Merchant, MerchantMembership, UserPlatformRole, Product, ProductCategory, ProductSku, Inventory


def test_authorization_and_membership(client):
    with next(app.dependency_overrides[get_db]()) as db:
        users = [User(username=name, mobile=str(13000000000+i), password_hash='x', mobile_verified_at=datetime.now(timezone.utc).replace(tzinfo=None), status='active') for i, name in enumerate(('platform', 'owner', 'staff', 'outsider'))]
        shops = [Merchant(name='A', status='active'), Merchant(name='B', status='active')]
        db.add_all(users + shops); db.flush()
        db.add_all([UserPlatformRole(user_id=users[0].id, role='platform_admin'), MerchantMembership(merchant_id=shops[0].id, user_id=users[1].id, role='admin', status='active'), MerchantMembership(merchant_id=shops[0].id, user_id=users[2].id, role='staff', status='active')])
        category = ProductCategory(merchant_id=shops[0].id, name='Drinks', status='active')
        product = Product(merchant_id=shops[0].id, name='Tea', status='active', skus=[ProductSku(name='Default', price=1, status='active', inventory=Inventory())]); db.add_all([product, category]); db.commit()
        headers = [{"Authorization": "Bearer " + tokens(user)['access_token']} for user in users]
        mid, other, pid, sid, cid = shops[0].id, shops[1].id, product.id, product.skus[0].id, category.id
        outsider_id, owner_id = users[3].id, users[1].id
    assert client.post('/api/v1/merchants', json={'name':'New'}).status_code == 401
    assert client.post('/api/v1/merchants', headers=headers[3], json={'name':'New'}).status_code == 403
    assert client.patch(f'/api/v1/products/{pid}', headers=headers[3], json={'name':'No'}).status_code == 403
    assert client.patch(f'/api/v1/products/{pid}', headers=headers[2], json={'name':'No'}).status_code == 403
    assert client.patch(f'/api/v1/products/{pid}', headers=headers[0], json={'name':'Platform'}).status_code == 200
    assert client.put(f'/api/v1/skus/{sid}/inventory', headers=headers[0], json={'available':3}).status_code == 200
    assert client.patch(f'/api/v1/products/{pid}', headers=headers[1], json={'name':'Yes'}).status_code == 200
    assert client.put(f'/api/v1/skus/{sid}/inventory', headers=headers[3], json={'available':5}).status_code == 403
    assert client.get(f'/api/v1/skus/{sid}/inventory', headers=headers[3]).status_code == 403
    assert client.post('/api/v1/categories', headers=headers[1], json={'merchant_id':other,'name':'No'}).status_code == 403
    for method, path, body in [
        ('PATCH', f'/api/v1/merchants/{mid}', {'name':'No'}),
        ('DELETE', f'/api/v1/merchants/{mid}', None),
        ('POST', '/api/v1/products', {'merchant_id':mid,'name':'No','price':'1'}),
        ('DELETE', f'/api/v1/products/{pid}', None),
        ('PATCH', f'/api/v1/categories/{cid}', {'name':'No'}),
        ('DELETE', f'/api/v1/categories/{cid}', None),
        ('POST', f'/api/v1/products/{pid}/skus', {'name':'No','price':'1'}),
        ('PATCH', f'/api/v1/skus/{sid}', {'name':'No'}),
        ('DELETE', f'/api/v1/skus/{sid}', None),
    ]:
        assert client.request(method, path, headers=headers[3], json=body).status_code == 403
    assert client.get(f'/api/v1/skus/{sid}/inventory', headers=headers[2]).status_code == 200
    assert client.get('/api/v1/users/me/permissions', headers=headers[1]).json()['memberships'][0]['role'] == 'admin'
    assert client.get(f'/api/v1/merchants/{mid}/members', headers=headers[2]).status_code == 403
    assert client.post(f'/api/v1/merchants/{mid}/members', headers=headers[1], json={'user_id':outsider_id,'role':'staff'}).status_code == 201
    assert client.patch(f'/api/v1/merchants/{mid}/members/{outsider_id}', headers=headers[1], json={'role':'admin'}).status_code == 200
    assert client.delete(f'/api/v1/merchants/{mid}/members/{outsider_id}', headers=headers[1]).status_code == 204
    assert client.delete(f'/api/v1/merchants/{mid}/members/{owner_id}', headers=headers[1]).status_code == 409


def test_bootstrap_only_once(client):
    from app.identity.bootstrap import bootstrap
    with next(app.dependency_overrides[get_db]()) as db:
        user = User(username='admin', mobile='13000000001', password_hash='x', mobile_verified_at=datetime.now(timezone.utc).replace(tzinfo=None), status='active')
        db.add(user); db.commit()
        bootstrap(db, user.id)
        assert db.query(UserPlatformRole).filter_by(user_id=user.id, role='super_admin').first()
        with pytest.raises(ValueError, match='已存在'):
            bootstrap(db, user.id)


def test_inactive_resources_are_not_public(client):
    with next(app.dependency_overrides[get_db]()) as db:
        owner = User(username='owner', mobile='13000000002', password_hash='x', mobile_verified_at=datetime.now(timezone.utc).replace(tzinfo=None), status='active')
        shop = Merchant(name='hidden', status='inactive')
        db.add_all([owner, shop]); db.flush()
        db.add(MerchantMembership(merchant_id=shop.id, user_id=owner.id, role='admin', status='active'))
        product = Product(merchant_id=shop.id, name='hidden', status='inactive', skus=[ProductSku(name='Default', price=1, status='active', inventory=Inventory())])
        db.add(product); db.commit()
        mid, pid, sid = shop.id, product.id, product.skus[0].id
        headers = {'Authorization': 'Bearer ' + tokens(owner)['access_token']}
    assert client.get('/api/v1/merchants').json() == []
    assert client.get('/api/v1/products').json() == []
    assert client.get(f'/api/v1/merchants/{mid}').status_code == 404
    assert client.get(f'/api/v1/products/{pid}').status_code == 404
    assert client.get(f'/api/v1/skus/{sid}').status_code == 404
    assert client.get(f'/api/v1/products/{pid}', headers=headers).status_code == 200
    assert client.get(f'/api/v1/skus/{sid}', headers=headers).status_code == 200


def test_platform_admin_can_manage_platform_roles(client):
    with next(app.dependency_overrides[get_db]()) as db:
        users = [User(username=name, mobile=str(13000000010+i), password_hash='x', mobile_verified_at=datetime.now(timezone.utc).replace(tzinfo=None), status='active') for i, name in enumerate(('root', 'other'))]
        db.add_all(users); db.flush()
        db.add(UserPlatformRole(user_id=users[0].id, role='platform_admin')); db.commit()
        root_id, other_id = users[0].id, users[1].id
        root, other = [{'Authorization': 'Bearer ' + tokens(user)['access_token']} for user in users]
    assert client.get('/api/v1/admin/users').status_code == 401
    assert client.get('/api/v1/admin/users', headers=other).status_code == 403
    assert len(client.get('/api/v1/admin/users', headers=root).json()) == 2
    assert client.get('/api/v1/admin/users?keyword=oth', headers=root).headers['x-total-count'] == '1'
    assert [item['username'] for item in client.get('/api/v1/admin/users?keyword=oth&status=active', headers=root).json()] == ['other']
    assert client.get('/api/v1/admin/users?status=inactive', headers=root).json() == []
    assert client.get('/api/v1/admin/users?status=unknown', headers=root).status_code == 422
    assert client.delete(f'/api/v1/admin/users/{root_id}/platform-admin', headers=root).status_code == 409
    with next(app.dependency_overrides[get_db]()) as db:
        db.add(UserPlatformRole(user_id=root_id, role='super_admin'))
        db.commit()

    assert client.put(f'/api/v1/admin/users/{other_id}/platform-admin', headers=other).status_code == 403
    assert client.put(f'/api/v1/admin/users/{other_id}/platform-admin', headers=root).status_code == 204
    assert next(item for item in client.get('/api/v1/admin/users', headers=root).json() if item['id']==root_id)['super_admin'] is True
    assert client.delete(f'/api/v1/admin/users/{root_id}/platform-admin', headers=other).status_code == 409
    assert client.delete(f'/api/v1/admin/users/{other_id}/platform-admin', headers=root).status_code == 204
    with next(app.dependency_overrides[get_db]()) as db:
        db.add(UserPlatformRole(user_id=other_id, role='platform_admin'))
        db.get(User, other_id).status = 'inactive'
        db.commit()
    assert client.delete(f'/api/v1/admin/users/{root_id}/platform-admin', headers=root).status_code == 409


def test_admin_creates_user_without_granting_roles(client):
    with next(app.dependency_overrides[get_db]()) as db:
        users = [User(username=name, mobile=str(13000000020+i), password_hash='x', mobile_verified_at=datetime.now(timezone.utc).replace(tzinfo=None), status='active') for i, name in enumerate(('root', 'other'))]
        db.add_all(users); db.flush()
        db.add(UserPlatformRole(user_id=users[0].id, role='platform_admin')); db.commit()
        admin, ordinary = [{'Authorization': 'Bearer ' + tokens(user)['access_token']} for user in users]
    payload = {'username':'newuser', 'mobile':'13800138999', 'password':'Password123', 'nickname':'新用户'}
    assert client.post('/api/v1/admin/users', json=payload).status_code == 401
    assert client.post('/api/v1/admin/users', json=payload, headers=ordinary).status_code == 403
    assert client.post('/api/v1/admin/users', json={**payload, 'password':'short'}, headers=admin).status_code == 422
    response = client.post('/api/v1/admin/users', json=payload, headers=admin)
    assert response.status_code == 201
    assert 'password' not in response.json() and 'password_hash' not in response.json()
    with next(app.dependency_overrides[get_db]()) as db:
        created = db.get(User, response.json()['id'])
        assert created.mobile_verified_at is None
        assert not db.query(UserPlatformRole).filter_by(user_id=created.id).first()
    assert client.post('/api/v1/admin/users', json=payload, headers=admin).status_code == 409
    assert client.post('/api/v1/admin/users', json={**payload, 'username':'unique'}, headers=admin).status_code == 409
    assert client.post('/api/v1/auth/login', json={'username':'newuser', 'password':'Password123'}).status_code == 200
    code = client.post('/api/v1/auth/codes', json={'mobile':payload['mobile'], 'purpose':'login'}).json()['code']
    assert client.post('/api/v1/auth/login/sms', json={'mobile':payload['mobile'], 'code':code}).status_code == 200
    with next(app.dependency_overrides[get_db]()) as db:
        assert db.get(User, response.json()['id']).mobile_verified_at is not None

def test_manageable_merchant_search_and_pagination(client):
    with next(app.dependency_overrides[get_db]()) as db:
        users = [User(username=n, mobile=str(13000000060+i), password_hash='x', status='active') for i,n in enumerate(('platform2','owner2','staff2'))]
        shops = [Merchant(name=n, status='active') for n in ('茶馆一','茶馆二','其他')]
        db.add_all(users + shops); db.flush()
        db.add_all([UserPlatformRole(user_id=users[0].id, role='platform_admin'), MerchantMembership(user_id=users[1].id, merchant_id=shops[1].id, role='admin', status='active'), MerchantMembership(user_id=users[2].id, merchant_id=shops[0].id, role='staff', status='active')]); db.commit()
        headers = [{'Authorization':'Bearer '+tokens(u)['access_token']} for u in users]
        ids = [s.id for s in shops]
    path='/api/v1/merchants/manageable'
    assert client.get(path).status_code == 401
    assert [m['id'] for m in client.get(path, headers=headers[1]).json()] == [ids[1]]
    assert client.get(path, headers=headers[2]).json() == []
    assert [m['id'] for m in client.get(path, params={'keyword':'茶馆','offset':1,'limit':1}, headers=headers[0]).json()] == [ids[1]]
    assert [m['id'] for m in client.get(path, params={'keyword':str(ids[2])}, headers=headers[0]).json()] == [ids[2]]
