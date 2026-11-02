"""开发版注册、登录和当前用户接口。"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.identity import crud, schema, service

router = APIRouter(prefix="/api/v1", tags=["用户认证"])
bearer = HTTPBearer(auto_error=False)

def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)):
    """从访问令牌获取有效用户。"""
    if credentials is None: raise HTTPException(401, "请先登录")
    return service.token_user(db, credentials.credentials, "access")

def optional_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)):
    if credentials is None:
        return None
    return service.token_user(db, credentials.credentials, "access")

@router.post("/auth/codes", summary="获取模拟验证码")
def code(data: schema.CodeRequest):
    """开发或测试环境返回模拟验证码。"""
    return {"code": service.issue_code(data.mobile, data.purpose), "expires_in": 300}

@router.post("/auth/register", response_model=schema.UserRead, status_code=201, summary="注册用户")
def register(data: schema.RegisterRequest, db: Session = Depends(get_db)):
    """验证手机号并创建账号。"""
    return service.register(db, data)

@router.post("/auth/login", summary="账号密码登录")
def login(data: schema.PasswordLogin, db: Session = Depends(get_db)):
    """校验账号密码并签发令牌。"""
    user = crud.by_username(db, data.username)
    if not user or user.status != "active" or not service.verify_password(data.password, user.password_hash):
        raise HTTPException(401, "账号或密码错误，或账号已停用")
    return service.tokens(user)

@router.post("/auth/login/sms", summary="手机号验证码登录")
def login_sms(data: schema.SmsLogin, db: Session = Depends(get_db)):
    """校验手机号验证码并签发令牌。"""
    service.consume_code(data.mobile, "login", data.code)
    user = crud.by_mobile(db, data.mobile)
    if not user or user.status != "active": raise HTTPException(401, "账号不存在或已停用")
    if user.mobile_verified_at is None:
        user.mobile_verified_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()
    return service.tokens(user)

@router.post("/auth/refresh", summary="刷新访问令牌")
def refresh(data: schema.RefreshRequest, db: Session = Depends(get_db)):
    """校验刷新令牌并签发新令牌。"""
    return service.tokens(service.token_user(db, data.refresh_token, "refresh"))

@router.get("/users/me", response_model=schema.UserRead, summary="查看当前用户")
def me(user = Depends(current_user)):
    """返回已登录用户的信息。"""
    return user

@router.patch("/users/me", response_model=schema.UserRead, summary="修改昵称")
def update_me(data: schema.ProfileUpdate, user = Depends(current_user), db: Session = Depends(get_db)):
    """修改当前用户昵称，不允许修改登录账号。"""
    user.nickname = data.nickname
    db.commit()
    db.refresh(user)
    return user
