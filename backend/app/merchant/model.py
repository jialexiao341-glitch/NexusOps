"""第一阶段数据库模型；具体业务规则由服务层落实。"""
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

ID = BigInteger().with_variant(Integer, "sqlite")

def utcnow():
    """返回用于数据库存储的 UTC 时间。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)

class Timestamps:
    """记录创建和最后修改时间。"""
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

class User(Timestamps, Base):
    """用户账户与登录信息。"""
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    mobile: Mapped[str] = mapped_column(String(20), unique=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    nickname: Mapped[str | None] = mapped_column(String(80))
    mobile_verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")

class Merchant(Timestamps, Base):
    """商户基本信息。"""
    __tablename__ = "merchants"
    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    description: Mapped[str | None] = mapped_column(String(500), default="")
    address: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default="pending")

class MerchantMembership(Timestamps, Base):
    """用户在商户内的角色。"""
    __tablename__ = "merchant_memberships"
    __table_args__ = (UniqueConstraint("merchant_id", "user_id"), Index("ix_memberships_user_status", "user_id", "status"))
    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    merchant_id: Mapped[int] = mapped_column(ID, ForeignKey("merchants.id", ondelete="RESTRICT"))
    user_id: Mapped[int] = mapped_column(ID, ForeignKey("users.id", ondelete="RESTRICT"))
    role: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="active")

class UserPlatformRole(Base):
    """用户的平台级角色。"""
    __tablename__ = "user_platform_roles"
    __table_args__ = (UniqueConstraint("user_id", "role"),)
    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ID, ForeignKey("users.id", ondelete="RESTRICT"))
    role: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

class ProductCategory(Timestamps, Base):
    """商户商品分类。"""
    __tablename__ = "product_categories"
    __table_args__ = (UniqueConstraint("merchant_id", "name"), Index("ix_categories_merchant_sort", "merchant_id", "sort_order", "id"))
    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    merchant_id: Mapped[int] = mapped_column(ID, ForeignKey("merchants.id", ondelete="RESTRICT"))
    name: Mapped[str] = mapped_column(String(120))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="active")

class Product(Timestamps, Base):
    """商品基本信息；价格由 SKU 管理。"""
    __tablename__ = "products"
    __table_args__ = (Index("ix_products_merchant_status", "merchant_id", "status", "id"),)
    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    merchant_id: Mapped[int] = mapped_column(ID, ForeignKey("merchants.id", ondelete="RESTRICT"))
    category_id: Mapped[int | None] = mapped_column(ID, ForeignKey("product_categories.id", ondelete="RESTRICT"))
    name: Mapped[str] = mapped_column(String(120), index=True)
    description: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="inactive")
    skus: Mapped[list["ProductSku"]] = relationship(back_populates="product", cascade="all, delete-orphan", order_by="ProductSku.id")

    @property
    def price(self):
        """兼容现有单规格接口，返回默认 SKU 的价格。"""
        return self.skus[0].price if self.skus else None

class ProductSku(Timestamps, Base):
    """可购买的商品规格。"""
    __tablename__ = "product_skus"
    __table_args__ = (CheckConstraint("price >= 0", name="ck_sku_price_nonnegative"),)
    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ID, ForeignKey("products.id", ondelete="RESTRICT"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(String(20), default="active")
    product: Mapped[Product] = relationship(back_populates="skus")
    inventory: Mapped["Inventory | None"] = relationship(back_populates="sku", cascade="all, delete-orphan", single_parent=True)

class Inventory(Base):
    """SKU 的可售及预留库存。"""
    __tablename__ = "inventory"
    __table_args__ = (CheckConstraint("available >= 0 AND reserved >= 0", name="ck_inventory_nonnegative"),)
    sku_id: Mapped[int] = mapped_column(ID, ForeignKey("product_skus.id", ondelete="RESTRICT"), primary_key=True)
    available: Mapped[int] = mapped_column(Integer, default=0)
    reserved: Mapped[int] = mapped_column(Integer, default=0)
    version: Mapped[int] = mapped_column(BigInteger, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    sku: Mapped[ProductSku] = relationship(back_populates="inventory")

class VoucherCampaign(Timestamps, Base):
    """优惠券销售活动及活动库存。"""
    __tablename__ = "voucher_campaigns"
    __table_args__ = (CheckConstraint("sale_price >= 0 AND total_stock >= 0 AND available_stock >= 0 AND available_stock <= total_stock", name="ck_campaign_stock_price"), CheckConstraint("starts_at < ends_at", name="ck_campaign_time"))
    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    merchant_id: Mapped[int] = mapped_column(ID, ForeignKey("merchants.id", ondelete="RESTRICT"), index=True)
    title: Mapped[str] = mapped_column(String(120))
    sale_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    total_stock: Mapped[int] = mapped_column(Integer)
    available_stock: Mapped[int] = mapped_column(Integer)
    starts_at: Mapped[datetime] = mapped_column(DateTime)
    ends_at: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20), default="draft")

class VoucherOrder(Timestamps, Base):
    """优惠券购买记录，限购及取消策略暂按草案实现。"""
    __tablename__ = "voucher_orders"
    __table_args__ = (UniqueConstraint("campaign_id", "user_id"), UniqueConstraint("user_id", "request_id"), CheckConstraint("amount_snapshot >= 0", name="ck_voucher_order_amount"))
    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    campaign_id: Mapped[int] = mapped_column(ID, ForeignKey("voucher_campaigns.id", ondelete="RESTRICT"))
    user_id: Mapped[int] = mapped_column(ID, ForeignKey("users.id", ondelete="RESTRICT"))
    request_id: Mapped[str] = mapped_column(String(64))
    amount_snapshot: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(String(20), default="created")

