from test_crud import business_client, client

def test_merchant_detail_cache(business_client, monkeypatch):
    from app.merchant import cache
    class FakeRedis:
        def __init__(self): self.data = {}
        def get(self, key): return self.data.get(key)
        def set(self, key, value, ex=None, nx=False, px=None):
            if nx and key in self.data: return False
            self.data[key] = value
            return True
        def delete(self, *keys):
            for key in keys: self.data.pop(key, None)
        def eval(self, script, nkeys, *args):
            if nkeys == 1:
                lock, token = args
                if self.data.get(lock) == token: self.data.pop(lock, None)
            else:
                lock, key, token, value, ttl = args
                if self.data.get(lock) == token:
                    self.data[key] = value
                    self.data.pop(lock, None)

    fake = FakeRedis()
    monkeypatch.setattr(cache, 'redis_client', fake)
    client = business_client
    mid = client.post('/api/v1/merchants', json={'name':'Before'}).json()['id']
    assert client.get(f'/api/v1/merchants/{mid}').json()['name'] == 'Before'
    assert fake.data
    assert client.patch(f'/api/v1/merchants/{mid}', json={'name':'After'}).status_code == 200
    assert client.get(f'/api/v1/merchants/{mid}').json()['name'] == 'After'
    assert client.get('/api/v1/merchants/99999').status_code == 404
    assert any('99999' in k for k in fake.data)
    monkeypatch.setattr(fake, 'get', lambda key: (_ for _ in ()).throw(cache.RedisError('offline')))
    assert client.get(f'/api/v1/merchants/{mid}').json()['name'] == 'After'

def test_cached_merchant_status_is_checked_in_database(business_client, monkeypatch):
    from app.merchant import cache
    from app.core.database import get_db
    from app.main import app
    from app.merchant.model import Merchant
    class FakeRedis:
        def __init__(self): self.data = {}
        def get(self, key): return self.data.get(key)
        def set(self, key, value, ex=None, nx=False, px=None):
            if nx and key in self.data: return False
            self.data[key] = value
            return True
        def delete(self, *keys):
            for key in keys: self.data.pop(key, None)
        def eval(self, script, nkeys, *args):
            if nkeys == 1:
                lock, token = args
                if self.data.get(lock) == token: self.data.pop(lock, None)
            else:
                lock, key, token, value, ttl = args
                if self.data.get(lock) == token:
                    self.data[key] = value
                    self.data.pop(lock, None)

    monkeypatch.setattr(cache, 'redis_client', FakeRedis())
    client = business_client
    mid = client.post('/api/v1/merchants', json={'name':'Private'}).json()['id']
    assert client.get(f'/api/v1/merchants/{mid}').status_code == 200
    with next(app.dependency_overrides[get_db]()) as db:
        db.get(Merchant, mid).status = 'inactive'
        db.commit()
    client.headers.pop('Authorization')
    assert client.get(f'/api/v1/merchants/{mid}').status_code == 404

def test_concurrent_cache_misses_share_one_database_load(monkeypatch):
    import threading
    import time
    from concurrent.futures import ThreadPoolExecutor
    from app.merchant import cache
    class RedisStub:
        def __init__(self): self.data = {}; self.lock = threading.Lock()
        def get(self, key):
            with self.lock: return self.data.get(key)
        def set(self, key, value, ex=None, nx=False, px=None):
            with self.lock:
                if nx and key in self.data: return False
                self.data[key] = value
                return True
        def eval(self, script, nkeys, *args):
            if nkeys == 1:
                lock_key, token = args
                with self.lock:
                    if self.data.get(lock_key) == token: return bool(self.data.pop(lock_key, None))
                    return 0
            lock_key, data_key, token, value, ttl = args
            with self.lock:
                if self.data.get(lock_key) != token: return 0
                self.data[data_key] = value
                self.data.pop(lock_key, None)
                return 1
    fake = RedisStub()
    monkeypatch.setattr(cache, 'redis_client', fake)
    count = 0
    mutex = threading.Lock()
    def load():
        nonlocal count
        with mutex: count += 1
        time.sleep(0.1)
        return cache.MerchantRead(id=42,name='Hot',description='',status='active')
    barrier = threading.Barrier(12)
    def run():
        barrier.wait()
        return cache.load_on_miss(42, load)
    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(lambda _: run(), range(12)))
    assert count == 1
    assert all(item.name == 'Hot' for item in results)

def test_invalidation_during_rebuild_prevents_stale_repopulation(monkeypatch):
    import threading
    from concurrent.futures import ThreadPoolExecutor
    from app.merchant import cache
    class RedisStub:
        def __init__(self): self.data={}; self.lock=threading.Lock()
        def get(self, key):
            with self.lock: return self.data.get(key)
        def set(self, key, value, ex=None, nx=False, px=None):
            with self.lock:
                if nx and key in self.data: return False
                self.data[key]=value; return True
        def delete(self, *keys):
            with self.lock:
                for key in keys: self.data.pop(key, None)
        def eval(self, script, nkeys, *args):
            with self.lock:
                if nkeys == 1:
                    lock, token=args
                    if self.data.get(lock)==token: self.data.pop(lock, None)
                else:
                    lock, key, token, value, ttl=args
                    if self.data.get(lock)==token:
                        self.data[key]=value; self.data.pop(lock, None)
    fake=RedisStub(); monkeypatch.setattr(cache,'redis_client',fake)
    entered=threading.Event(); release=threading.Event()
    def load():
        entered.set(); assert release.wait(2)
        return cache.MerchantRead(id=43,name='Old',description='',status='active')
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(cache.load_on_miss,43,load)
        assert entered.wait(2)
        cache.invalidate(43)
        release.set(); assert future.result().name=='Old'
    assert cache.key(43) not in fake.data


def test_lock_wait_timeout_falls_back_without_overwriting_cache(monkeypatch):
    from app.merchant import cache
    class LockedRedis:
        def get(self, key): return None
        def set(self, *args, **kwargs): return False
    monkeypatch.setattr(cache, 'redis_client', LockedRedis())
    monkeypatch.setattr(cache, 'WAIT_SECONDS', 0)
    assert cache.load_on_miss(1, lambda: 'database') == 'database'
