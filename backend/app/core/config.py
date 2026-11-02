"""根据运行环境加载配置，进程环境变量优先于环境文件。"""
import os
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]

def environment_file():
    """返回指定环境的配置文件；不接受未知环境。"""
    name = os.environ.get("NEXUSOPS_ENV", "dev")
    if name not in {"dev", "test", "prod"}:
        raise ValueError("NEXUSOPS_ENV 必须为 dev、test 或 prod")
    return BACKEND_DIR / "env" / f".env.{name}"

class Settings(BaseSettings):
    """加载所选环境配置，数据库和 Redis 地址必须显式提供。"""
    model_config = SettingsConfigDict(extra="ignore")
    database_url: str = Field(min_length=1)
    redis_url: str = Field(min_length=1)
    jwt_secret: str = Field(min_length=32)

settings = Settings(_env_file=environment_file(), _env_file_encoding="utf-8")
