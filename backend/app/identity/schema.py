"""身份认证和用户资料接口的数据格式。"""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

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
class ProfileUpdate(BaseModel):
    """只允许更新昵称。"""
    model_config = ConfigDict(extra="forbid")
    nickname: str | None = Field(max_length=80)
class RefreshRequest(BaseModel):
    """提交刷新令牌以获取新访问令牌。"""
    refresh_token: str
