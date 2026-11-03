from test_crud import client

def test_registration_and_login(client):
    result = client.post("/api/v1/auth/codes", json={"mobile": "13800138000", "purpose": "register"})
    assert result.status_code == 200
    code = result.json()["code"]
    register = client.post("/api/v1/auth/register", json={"mobile":"13800138000", "code":code, "username":"alice", "password":"password123", "nickname":"小李"})
    assert register.status_code == 201
    assert client.post("/api/v1/auth/register", json={"mobile":"13800138000", "code":code, "username":"alice", "password":"password123"}).status_code == 400
    login = client.post("/api/v1/auth/login", json={"username":"alice", "password":"password123"})
    assert login.status_code == 200
    token = login.json()["access_token"]
    assert client.get("/api/v1/users/me", headers={"Authorization":f"Bearer {token}"}).json()["nickname"] == "小李"
    assert client.patch("/api/v1/users/me", json={"nickname":"新昵称"}, headers={"Authorization":f"Bearer {token}"}).json()["nickname"] == "新昵称"
    assert client.post("/api/v1/auth/login", json={"username":"alice", "password":"wrongpass"}).status_code == 401
    code = client.post("/api/v1/auth/codes", json={"mobile":"13800138000", "purpose":"login"}).json()["code"]
    assert client.post("/api/v1/auth/login/sms", json={"mobile":"13800138000", "code":code}).status_code == 200
    assert client.post("/api/v1/auth/login/sms", json={"mobile":"13800138000", "code":code}).status_code == 400


def test_auth_boundaries(client, monkeypatch):
    from app.identity.service import issue_code
    from fastapi import HTTPException
    import pytest
    monkeypatch.setenv("NEXUSOPS_ENV", "prod")
    with pytest.raises(HTTPException) as exc:
        issue_code("13800138001", "register")
    assert exc.value.status_code == 503
    monkeypatch.setenv("NEXUSOPS_ENV", "test")
    assert client.get("/api/v1/users/me").status_code == 401
    assert client.patch("/api/v1/users/me", json={"username": "changed"}).status_code == 401

def test_avatar_persistence_and_validation(client):
    import base64
    code = client.post('/api/v1/auth/codes', json={'mobile':'13800138010','purpose':'register'}).json()['code']
    client.post('/api/v1/auth/register', json={'mobile':'13800138010','code':code,'username':'avatar_user','password':'password123'})
    token = client.post('/api/v1/auth/login', json={'username':'avatar_user','password':'password123'}).json()['access_token']
    headers = {'Authorization':f'Bearer {token}'}
    avatar = 'data:image/jpeg;base64,' + base64.b64encode(b'\xff\xd8\xffexample\xff\xd9').decode()
    assert client.put('/api/v1/users/me/avatar', json={'avatar':avatar}, headers=headers).json()['avatar'] == avatar
    assert client.get('/api/v1/users/me', headers=headers).json()['avatar'] == avatar
    assert client.put('/api/v1/users/me/avatar', json={'avatar':'data:image/svg+xml;base64,PHN2Zz4='}, headers=headers).status_code == 422
    assert client.put('/api/v1/users/me/avatar', json={'avatar':None}, headers=headers).json()['avatar'] is None
    assert client.put('/api/v1/users/me/avatar', json={'avatar':avatar}).status_code == 401
