"""商户详情的短期缓存；Redis 故障不阻断数据库查询。"""
import logging
import random
import time
import uuid
import redis
from redis.exceptions import RedisError
from pydantic import ValidationError
from app.core.config import settings
from app.merchant.schema import MerchantRead

logger = logging.getLogger(__name__)
redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=0.2, socket_timeout=0.2)
MISSING = "null"
LOCK_MS = 3000
WAIT_SECONDS = 0.5
POLL_SECONDS = 0.025
PUBLISH = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    redis.call('set', KEYS[2], ARGV[2], 'EX', ARGV[3])
    redis.call('del', KEYS[1])
    return 1
end
return 0
"""
RELEASE = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
end
return 0
"""

def key(item_id):
    return f"nexusops:merchant:detail:v1:{item_id}"

def lock_key(item_id):
    return f"{key(item_id)}:lock"

def decode(value):
    if value is None or value == MISSING:
        return value
    return MerchantRead.model_validate_json(value)

def get(item_id):
    try:
        value = redis_client.get(key(item_id))
        return decode(value)
    except (RedisError, ValidationError, ValueError):
        logger.warning("商户缓存读取失败，回源数据库", exc_info=True)
        return None

def put(item_id, item):
    try:
        value = MISSING if item is None else MerchantRead.model_validate(item).model_dump_json()
        redis_client.set(key(item_id), value, ex=30 if item is None else 300 + random.randint(0, 60))
    except (RedisError, ValidationError, ValueError):
        logger.warning("商户缓存写入失败", exc_info=True)

def invalidate(item_id):
    try:
        redis_client.delete(key(item_id), lock_key(item_id))
    except RedisError:
        logger.warning("商户缓存失效失败，将在过期后恢复", exc_info=True)

def load_on_miss(item_id, loader):
    """合并并发缓存重建；Redis 故障或等待超时直接查询数据库。"""
    token = uuid.uuid4().hex
    deadline = time.monotonic() + WAIT_SECONDS
    loaded = False
    loading = False
    item = None
    try:
        while True:
            cached = decode(redis_client.get(key(item_id)))
            if cached is not None:
                return None if cached == MISSING else cached
            if redis_client.set(lock_key(item_id), token, nx=True, px=LOCK_MS):
                try:
                    cached = decode(redis_client.get(key(item_id)))
                    if cached is not None:
                        return None if cached == MISSING else cached
                    loading = True
                    item = loader()
                    loading = False
                    loaded = True
                    value = MISSING if item is None else MerchantRead.model_validate(item).model_dump_json()
                    ttl = 30 if item is None else 300 + random.randint(0, 60)
                    redis_client.eval(PUBLISH, 2, lock_key(item_id), key(item_id), token, value, ttl)
                    return item
                finally:
                    try:
                        redis_client.eval(RELEASE, 1, lock_key(item_id), token)
                    except RedisError:
                        logger.warning('商户缓存锁释放失败，将等待锁过期', exc_info=True)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                loading = True
                return loader()
            time.sleep(min(POLL_SECONDS, remaining))
    except (RedisError, ValidationError, ValueError):
        if loading:
            raise
        logger.warning('商户缓存重建失败，回源数据库', exc_info=True)
        return item if loaded else loader()
