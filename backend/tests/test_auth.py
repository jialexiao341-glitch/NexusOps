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
