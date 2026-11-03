import pytest
from redis.exceptions import ConnectionError

@pytest.fixture(autouse=True)
def isolate_redis(monkeypatch):
    """测试不得读取或修改开发环境的 Redis。"""
    from app.merchant import cache
    class OfflineRedis:
        def get(self, key): raise ConnectionError('test cache unavailable')
        def set(self, key, value, ex): raise ConnectionError('test cache unavailable')
        def delete(self, *keys): raise ConnectionError('test cache unavailable')
    monkeypatch.setattr(cache, 'redis_client', OfflineRedis())
