import logging
from fastapi import FastAPI
from app.merchant.controller import router
from app.merchant.catalog import router as catalog_router
from app.identity.controller import router as identity_router
from app.identity.members import router as members_router

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="NexusOps API")
app.include_router(router)
app.include_router(catalog_router)
app.include_router(identity_router)
app.include_router(members_router)

@app.get("/health", tags=["health"])
def health():
    """返回 API 进程存活状态，不检查依赖服务。"""
    return {"status": "ok"}

