"""身份认证和用户资料接口的数据格式。"""
import base64
import binascii
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

class CodeRequest(BaseModel):
    """请求发送指定用途的验证码。"""
    mobile: str = Field(pattern=r"^1[3-9][0-9]{9}$")
    purpose: Literal["register", "login"]
class RegisterRequest(BaseModel):
    """手机号验证后创建账号。"""
    mobile: str = Field(pattern=r"^1[3-9][0-9]{9}$")
    code: str = Field(pattern=r"^[0-9]{6}$")
    username: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_]+$")
    password: str = Field(min_length=8, max_length=128)
    nickname: str | None = Field(default=None, max_length=80)
class AdminUserCreate(BaseModel):
    """平台管理员创建普通账号，手机号初始未验证。"""
    model_config = ConfigDict(extra="forbid")
    mobile: str = Field(pattern=r"^1[3-9][0-9]{9}$")
    username: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_]+$")
    password: str = Field(min_length=8, max_length=128)
    nickname: str | None = Field(default=None, max_length=80)
class PasswordLogin(BaseModel):
    """账号密码登录。"""
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)
class SmsLogin(BaseModel):
    """手机号验证码登录。"""
    mobile: str = Field(pattern=r"^1[3-9][0-9]{9}$")
    code: str = Field(pattern=r"^[0-9]{6}$")
class UserRead(BaseModel):
    """返回用户资料，不包含密码。"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    mobile: str
    nickname: str | None
    status: str
    avatar: str | None = None

class AvatarUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    avatar: str | None = Field(max_length=48000)

    @field_validator("avatar")
    @classmethod
    def validate_avatar(cls, value):
        if value is None: return None
        prefix = "data:image/jpeg;base64,"
        if not value.startswith(prefix): raise ValueError("头像格式无效")
        try: image = base64.b64decode(value[len(prefix):], validate=True)
        except (binascii.Error, ValueError): raise ValueError("头像格式无效")
        if not image.startswith(b"\xff\xd8\xff") or not image.endswith(b"\xff\xd9"): raise ValueError("头像格式无效")
        return value

class ProfileUpdate(BaseModel):
    """只允许更新昵称。"""
    model_config = ConfigDict(extra="forbid")
    nickname: str | None = Field(max_length=80)
class RefreshRequest(BaseModel):
    """提交刷新令牌以获取新访问令牌。"""
    refresh_token: str
