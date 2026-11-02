import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.core.database import Base, get_db
from app.main import app

@pytest.fixture
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    def override():
        with factory() as session:
            yield session
    app.dependency_overrides[get_db] = override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    engine.dispose()

def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}

def test_merchant_and_product_crud(client):
    merchant = client.post("/api/v1/merchants", json={"name": "Shop"})
    assert merchant.status_code == 201
    mid = merchant.json()["id"]
    product = client.post("/api/v1/products", json={"merchant_id": mid, "name": "Tea", "price": "12.50"})
    assert product.status_code == 201
    pid = product.json()["id"]
    assert len(client.get("/api/v1/products").json()) == 1
    assert client.get(f"/api/v1/merchants/{mid}").json()["name"] == "Shop"
    assert client.patch(f"/api/v1/products/{pid}", json={"price": "15.00"}).json()["price"] == "15.00"
    assert client.delete(f"/api/v1/merchants/{mid}").status_code == 409
    assert client.delete(f"/api/v1/products/{pid}").status_code == 204
    assert client.delete(f"/api/v1/merchants/{mid}").status_code == 204
    assert client.get(f"/api/v1/products/{pid}").status_code == 404

def test_validation_and_missing_merchant(client):
    assert client.post("/api/v1/products", json={"merchant_id": 999, "name": "Tea", "price": "1.00"}).status_code == 404
    assert client.post("/api/v1/products", json={"merchant_id": 1, "name": "Tea", "price": "-1"}).status_code == 422
    mid = client.post("/api/v1/merchants", json={"name": "Shop"}).json()["id"]
    assert client.patch(f"/api/v1/merchants/{mid}", json={"name": None}).status_code == 422
    assert client.get("/api/v1/merchants?limit=101").status_code == 422

def test_category_sku_inventory_flow(client):
    api = '/api/v1'
    mid = client.post(api + '/merchants', json={'name': 'Shop'}).json()['id']
    other = client.post(api + '/merchants', json={'name': 'Other'}).json()['id']
    category = client.post(api + '/categories', json={'merchant_id': mid, 'name': 'Drinks'})
    assert category.status_code == 201
    cid = category.json()['id']
    assert client.post(api + '/categories', json={'merchant_id': mid, 'name': 'Drinks'}).status_code == 409
    assert client.post(api + '/products', json={'merchant_id': other, 'category_id': cid, 'name': 'Tea', 'price': '5'}).status_code == 422
    pid = client.post(api + '/products', json={'merchant_id': mid, 'category_id': cid, 'name': 'Tea', 'price': '5'}).json()['id']
    assert client.delete(f'{api}/categories/{cid}').status_code == 409
    assert client.get(f'{api}/categories?merchant_id={mid}').json()[0]['id'] == cid
    assert client.patch(f'{api}/categories/{cid}', json={'name': 'Tea'}).status_code == 200
    skus = client.get(f'{api}/products/{pid}/skus').json()
    assert client.delete(f"{api}/skus/{skus[0]['id']}").status_code == 409
    sku = client.post(f'{api}/products/{pid}/skus', json={'name': 'Large', 'price': '7.50'})
    assert sku.status_code == 201
    sid = sku.json()['id']
    assert client.patch(f'{api}/skus/{sid}', json={'price': '8.00'}).json()['price'] == '8.00'
    assert client.put(f'{api}/skus/{sid}/inventory', json={'available': 12}).json()['available'] == 12
    assert client.put(f'{api}/skus/{sid}/inventory', json={'available': -1}).status_code == 422
    assert client.get(f'{api}/skus/{sid}/inventory').json()['available'] == 12
    assert client.delete(f'{api}/skus/{sid}').status_code == 204
    assert client.delete(f'{api}/products/{pid}').status_code == 204
    assert client.delete(f'{api}/categories/{cid}').status_code == 204
