"""商户与商品接口的请求和响应数据结构。"""
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from app.merchant.enum import MerchantCategory

Status = Literal["active", "inactive"]
class MerchantCreate(BaseModel):
    """创建商户时提交的数据。"""
    name: str = Field(min_length=1, max_length=120, description="名称")
    category: MerchantCategory | None = None
    description: str = Field(default="", max_length=500, description="商户描述")
    status: Status = "active"
class MerchantUpdate(BaseModel):
    """部分更新商户时提交的数据。"""
    name: str | None = Field(default=None, min_length=1, max_length=120)
    category: MerchantCategory | None = None
    description: str | None = Field(default=None, max_length=500)
    status: Status | None = None
class MerchantRead(MerchantCreate):
    """返回给客户端的商户信息。"""
    model_config = ConfigDict(from_attributes=True)
    id: int
class ProductCreate(BaseModel):
    """创建商品时提交的数据。"""
    merchant_id: int = Field(gt=0, description="所属商户 ID")
    category_id: int | None = Field(default=None, gt=0)
    name: str = Field(min_length=1, max_length=120, description="名称")
    price: Decimal = Field(ge=0, max_digits=10, decimal_places=2, description="商品价格，最多两位小数")
    status: Status = "active"
class ProductUpdate(BaseModel):
    """部分更新商品时提交的数据。"""
    category_id: int | None = Field(default=None, gt=0)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    price: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    status: Status | None = None
class ProductRead(ProductCreate):
    """返回给客户端的商品信息。"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    merchant_name: str
    category_name: str | None

