"""本机开发环境只读商户详情的缓存击穿对照；使用临时 Redis 键。"""
import json
import os
import statistics
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy.engine import make_url
from app.core.config import settings
from app.core.database import SessionLocal
from app.merchant import cache
from app.merchant.model import Merchant
from app.merchant.schema import MerchantRead

WORKERS = 24
DELAY_SECONDS = 0.1  # 模拟数据库回源耗时，便于复现同时失效。

def main():
    target = make_url(settings.database_url)
    if os.environ.get('NEXUSOPS_ENV') != 'dev' or target.host not in ('localhost', '127.0.0.1') or target.database != 'nexusops':
        raise SystemExit('仅允许本机 nexusops 开发数据库')
    with SessionLocal() as db:
        merchant = db.get(Merchant, 3)
        if merchant is None:
            raise SystemExit('商户 3 不存在，无法运行实验')
    cache.redis_client.ping()
    results = []
    for protected in (False, True):
        experiment_id = 'experiment-' + uuid.uuid4().hex
        barrier = threading.Barrier(WORKERS)
        mutex = threading.Lock()
        counter = [0]
        def loader():
            with mutex: counter[0] += 1
            with SessionLocal() as db:
                item = MerchantRead.model_validate(db.get(Merchant, 3))
            time.sleep(DELAY_SECONDS)
            return item
        def request(_):
            barrier.wait()
            start = time.perf_counter()
            if protected:
                item = cache.load_on_miss(experiment_id, loader)
            else:
                item = cache.get(experiment_id)
                if item is None:
                    item = loader()
                    cache.put(experiment_id, item)
            return (time.perf_counter() - start) * 1000, item.id == 3
        try:
            with ThreadPoolExecutor(max_workers=WORKERS) as pool:
                observations = list(pool.map(request, range(WORKERS)))
            times = sorted(t for t, _ in observations)
            results.append({'mode': 'protected' if protected else 'baseline', 'requests': WORKERS,
                            'full_detail_loads': counter[0], 'errors': sum(not ok for _, ok in observations),
                            'p50_ms': round(statistics.median(times), 1), 'p95_ms': round(times[int(0.95 * (len(times) - 1))], 1),
                            'p99_ms': round(times[int(0.99 * (len(times) - 1))], 1), 'latencies_ms': [round(t, 1) for t in times]})
        finally:
            cache.redis_client.delete(cache.key(experiment_id), cache.lock_key(experiment_id))
    print(json.dumps({'workers': WORKERS, 'artificial_delay_ms': DELAY_SECONDS * 1000, 'results': results}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
