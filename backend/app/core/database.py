from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.core.config import settings

class Base(DeclarativeBase):
    """所有 ORM 模型共享的声明式基类。"""
    pass

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

def get_db():
    """为每次请求提供数据库会话，并在请求结束后关闭。"""
    with SessionLocal() as session:
        yield session
