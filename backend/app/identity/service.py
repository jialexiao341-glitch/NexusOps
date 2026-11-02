"""身份验证业务与开发环境模拟验证码。"""
import hashlib
import hmac
import os
import secrets
import threading
import time
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from app.core.config import settings
from app.identity import crud
from app.merchant.model import User

_codes = {}
_lock = threading.Lock()

def issue_code(mobile, purpose):
    """仅在开发和测试环境生成一次性模拟验证码。"""
    if os.getenv("NEXUSOPS_ENV", "dev") not in ("dev", "test"):
        raise HTTPException(503, "模拟验证码在当前环境不可用")
    code = f"{secrets.randbelow(1000000):06d}"
    with _lock:
        now = time.monotonic()
        for key, entry in list(_codes.items()):
            if entry[1] <= now:
                del _codes[key]
        old = _codes.get((mobile, purpose))
        if old and now - old[3] < 30:
            raise HTTPException(429, "请求过于频繁，请稍后再试")
        _codes[(mobile, purpose)] = (hashlib.sha256(code.encode()).digest(), now + 300, 0, now)
    return code

def consume_code(mobile, purpose, code):
    """校验过期时间和错误次数，成功后使验证码失效。"""
    if os.getenv("NEXUSOPS_ENV", "dev") not in ("dev", "test"):
        raise HTTPException(503, "验证码服务尚未配置")
    with _lock:
        key = (mobile, purpose)
        item = _codes.get(key)
        if not item or item[1] <= time.monotonic():
            _codes.pop(key, None)
            raise HTTPException(400, "验证码无效或已过期")
        if not hmac.compare_digest(item[0], hashlib.sha256(code.encode()).digest()):
            attempts = item[2] + 1
            if attempts >= 5: _codes.pop(key, None)
            else: _codes[key] = (item[0], item[1], attempts, item[3])
            raise HTTPException(400, "验证码无效或已过期")
        del _codes[key]

def hash_password(password):
    """使用随机盐和 scrypt 派生密码哈希。"""
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1)
    return f"scrypt$16384$8$1${salt.hex()}${digest.hex()}"

def verify_password(password, stored):
    """根据保存的参数验证密码。"""
    try:
        kind, n, r, p, salt, expected = stored.split("$")
        if (kind, n, r, p) != ("scrypt", "16384", "8", "1"): return False
        actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p))
        return hmac.compare_digest(actual, bytes.fromhex(expected))
    except (ValueError, TypeError):
        return False

def register(db, data):
    """校验验证码和账号唯一性后创建用户。"""
    consume_code(data.mobile, "register", data.code)
    if crud.by_mobile(db, data.mobile) or crud.by_username(db, data.username):
        raise HTTPException(409, "手机号或账号已存在")
    user = User(mobile=data.mobile, username=data.username, password_hash=hash_password(data.password), nickname=data.nickname, mobile_verified_at=datetime.now(timezone.utc).replace(tzinfo=None))
    db.add(user)
    try: db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "手机号或账号已存在")
    db.refresh(user)
    return user

def tokens(user):
    """签发短期访问令牌和刷新令牌。"""
    now = datetime.now(timezone.utc)
    def encode(kind, lifetime):
        return jwt.encode({"sub":str(user.id), "type":kind, "iat":now, "exp":now+lifetime}, settings.jwt_secret, algorithm="HS256")
    return {"access_token":encode("access", timedelta(minutes=30)), "refresh_token":encode("refresh", timedelta(days=7)), "token_type":"bearer"}

def token_user(db, token, expected):
    """验证令牌类型和账号状态。"""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"], options={"require":["exp", "iat", "sub"]})
        if payload.get("type") != expected: raise ValueError()
        user = db.get(User, int(payload["sub"]))
    except (jwt.PyJWTError, ValueError, TypeError):
        raise HTTPException(401, "登录凭证无效")
    if not user or user.status != "active": raise HTTPException(401, "账号不存在或已停用")
    return user
