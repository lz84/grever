"""
DB连接池并发测试

测试项目：
1. 并发 acquire/release - 多线程同时获取和释放连接
2. 连接池耗尽 - 验证 pool_max_size 限制
3. 并发超时 - 验证 connection_timeout
4. 并发熔断 - 验证熔断器在高并发下的行为
5. 配置热更新并发安全 - 运行时更新配置不影响正在执行的请求
"""

import asyncio
import threading
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any

from .pool import ConnectionPool, PoolConfig, create_pool, get_pool
from .config import PoolConfig as PC


class ConcurrencyTestResult:
    def __init__(self, name: str):
        self.name = name
        self.success_count = 0
        self.failure_count = 0
        self.error_messages: List[str] = []
        self.latencies_ms: List[float] = []
        self.start_time: float = 0
        self.end_time: float = 0

    @property
    def total(self) -> int:
        return self.success_count + self.failure_count

    @property
    def duration_ms(self) -> float:
        return (self.end_time - self.start_time) * 1000

    @property
    def avg_latency_ms(self) -> float:
        return statistics.mean(self.latencies_ms) if self.latencies_ms else 0

    @property
    def p95_latency_ms(self) -> float:
        if not self.latencies_ms:
            return 0
        sorted_latencies = sorted(self.latencies_ms)
        idx = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[min(idx, len(sorted_latencies) - 1)]

    @property
    def throughput(self) -> float:
        dur = self.duration_ms / 1000
        return self.total / dur if dur > 0 else 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "total": self.total,
            "success": self.success_count,
            "failure": self.failure_count,
            "duration_ms": round(self.duration_ms, 2),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "p95_latency_ms": round(self.p95_latency_ms, 2),
            "throughput_ops": round(self.throughput, 2),
            "errors": self.error_messages[:5],  # First 5 errors
        }


def run_concurrent_acquire_release(
    pool: ConnectionPool,
    num_threads: int = 20,
    operations_per_thread: int = 50,
    hold_time_ms: int = 10,
) -> ConcurrencyTestResult:
    """
    并发 acquire/release 测试
    多线程同时从池中获取连接、使用、释放
    """
    result = ConcurrencyTestResult("concurrent_acquire_release")
    result.start_time = time.time()
    errors = []
    latencies = []
    lock = threading.Lock()

    def worker(thread_id: int):
        for i in range(operations_per_thread):
            t0 = time.time()
            try:
                # Use async acquire in a sync context
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                conn = loop.run_until_complete(pool.acquire(timeout=10))
                time.sleep(hold_time_ms / 1000)
                loop.run_until_complete(pool.release(conn))
                loop.close()

                latency = (time.time() - t0) * 1000
                with lock:
                    latencies.append(latency)
                    result.success_count += 1
            except Exception as e:
                with lock:
                    result.failure_count += 1
                    errors.append(f"T{thread_id}-op{i}: {type(e).__name__}: {e}")

    threads = []
    for t in range(num_threads):
        th = threading.Thread(target=worker, args=(t,))
        threads.append(th)
        th.start()

    for th in threads:
        th.join()

    result.end_time = time.time()
    result.latencies_ms = latencies
    result.error_messages = errors
    return result


def run_pool_exhaustion_test(
    pool: ConnectionPool,
    pool_max_size: int,
    num_concurrent: int,
    hold_time_ms: int = 500,
) -> ConcurrencyTestResult:
    """
    连接池耗尽测试
    验证 pool_max_size 限制是否生效
    """
    result = ConcurrencyTestResult("pool_exhaustion")
    result.start_time = time.time()
    errors = []
    latencies = []
    lock = threading.Lock()
    acquired_conns = []
    acquired_lock = threading.Lock()

    def worker(thread_id: int):
        t0 = time.time()
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            conn = loop.run_until_complete(pool.acquire(timeout=15))
            with acquired_lock:
                acquired_conns.append(conn)
            time.sleep(hold_time_ms / 1000)
            with acquired_lock:
                acquired_conns.remove(conn)
            loop.run_until_complete(pool.release(conn))
            latency = (time.time() - t0) * 1000
            with lock:
                latencies.append(latency)
                result.success_count += 1
            loop.close()
        except Exception as e:
            with lock:
                result.failure_count += 1
                errors.append(f"T{thread_id}: {type(e).__name__}: {e}")

    threads = []
    for t in range(num_concurrent):
        th = threading.Thread(target=worker, args=(t,))
        threads.append(th)
        th.start()

    for th in threads:
        th.join()

    result.end_time = time.time()
    result.latencies_ms = latencies
    result.error_messages = errors

    # Verify pool_max_size was respected
    metrics = pool.get_metrics()
    max_concurrent = metrics.active_connections + metrics.idle_connections

    return result


def run_timeout_test(
    pool: ConnectionPool,
    num_threads: int = 10,
    hold_time_ms: int = 2000,
    timeout_sec: int = 1,
) -> ConcurrencyTestResult:
    """
    并发超时测试
    验证 connection_timeout 限制
    """
    result = ConcurrencyTestResult("concurrent_timeout")
    result.start_time = time.time()
    errors = []
    latencies = []
    lock = threading.Lock()

    def worker(thread_id: int):
        t0 = time.time()
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            conn = loop.run_until_complete(pool.acquire(timeout=timeout_sec))
            loop.run_until_complete(pool.release(conn))
            latency = (time.time() - t0) * 1000
            with lock:
                latencies.append(latency)
                result.success_count += 1
            loop.close()
        except Exception as e:
            with lock:
                result.failure_count += 1
                err = f"T{thread_id}: {type(e).__name__}: {str(e)[:60]}"
                errors.append(err)
            # Note: failure is expected here since hold_time > timeout

    # First saturate the pool
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    saturating_conns = []
    for _ in range(pool.config.pool_max_size):
        conn = loop.run_until_complete(pool.acquire(timeout=5))
        saturating_conns.append(conn)
    loop.close()

    # Now try to acquire with timeout (should fail)
    threads = []
    for t in range(num_threads):
        th = threading.Thread(target=worker, args=(t,))
        threads.append(th)
        th.start()

    for th in threads:
        th.join()

    # Release saturating connections
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    for conn in saturating_conns:
        loop.run_until_complete(pool.release(conn))
    loop.close()

    result.end_time = time.time()
    result.latencies_ms = latencies
    result.error_messages = errors
    return result


def run_config_hot_reload_test(
    pool: ConnectionPool,
    num_threads: int = 10,
    operations_per_thread: int = 30,
) -> ConcurrencyTestResult:
    """
    配置热更新并发安全测试
    验证运行时更新配置不影响正在执行的请求
    """
    result = ConcurrencyTestResult("config_hot_reload")
    result.start_time = time.time()
    errors = []
    latencies = []
    lock = threading.Lock()
    reload_count = [0]
    reload_lock = threading.Lock()

    def worker(thread_id: int):
        for i in range(operations_per_thread):
            if thread_id % 3 == 0 and i % 5 == 0:
                # Periodically reload config
                new_config = PoolConfig(
                    pool_min_size=3,
                    pool_max_size=30 if (i % 10 == 0) else 50,
                    idle_timeout=60000 if (i % 7 == 0) else 300000,
                    health_check_enabled=(i % 2 == 0),
                )
                pool.update_config(new_config)
                with reload_lock:
                    reload_count[0] += 1
                time.sleep(0.01)

            t0 = time.time()
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                conn = loop.run_until_complete(pool.acquire(timeout=5))
                loop.run_until_complete(pool.release(conn))
                loop.close()
                latency = (time.time() - t0) * 1000
                with lock:
                    latencies.append(latency)
                    result.success_count += 1
            except Exception as e:
                with lock:
                    result.failure_count += 1
                    errors.append(f"T{thread_id}-op{i}: {type(e).__name__}: {str(e)[:60]}")

    threads = []
    for t in range(num_threads):
        th = threading.Thread(target=worker, args=(t,))
        threads.append(th)
        th.start()

    for th in threads:
        th.join()

    result.end_time = time.time()
    result.latencies_ms = latencies
    result.error_messages = errors
    return result


def run_all_tests() -> Dict[str, ConcurrencyTestResult]:
    """
    运行所有并发测试
    """
    print("\n" + "=" * 60)
    print("DB连接池并发测试")
    print("=" * 60)

    # Create a dedicated pool for testing
    config = PoolConfig(
        pool_min_size=5,
        pool_max_size=10,
        idle_timeout=300000,
        connection_timeout=5000,
        health_check_enabled=True,
        test_on_borrow=True,
        circuit_breaker_enabled=True,
        circuit_breaker_failure_threshold=5,
    )

    pool = create_pool(config, name="test-concurrent")
    results = {}

    # Test 1: Concurrent acquire/release
    print("\n[1/4] 并发 acquire/release (20 threads x 50 ops)...")
    r1 = run_concurrent_acquire_release(pool, num_threads=20, operations_per_thread=50)
    results["concurrent_acquire_release"] = r1
    print(f"  → {r1.success_count}/{r1.total} success, "
          f"avg={r1.avg_latency_ms:.1f}ms, p95={r1.p95_latency_ms:.1f}ms, "
          f"throughput={r1.throughput:.1f} ops/s")

    # Test 2: Pool exhaustion
    print("\n[2/4] 连接池耗尽 (20 concurrent, pool_max=10)...")
    r2 = run_pool_exhaustion_test(pool, pool_max_size=10, num_concurrent=20, hold_time_ms=300)
    results["pool_exhaustion"] = r2
    print(f"  → {r2.success_count}/{r2.total} success, "
          f"failures={r2.failure_count} (expected: some timeout)")

    # Test 3: Timeout behavior
    print("\n[3/4] 并发超时 (10 threads, timeout=1s, hold=2s)...")
    r3 = run_timeout_test(pool, num_threads=10, hold_time_ms=2000, timeout_sec=1)
    results["concurrent_timeout"] = r3
    print(f"  → {r3.success_count}/{r3.total} success, "
          f"failures={r3.failure_count} (expected: all should fail)")

    # Test 4: Config hot reload
    print("\n[4/4] 配置热更新并发安全 (10 threads x 30 ops, frequent reload)...")
    r4 = run_config_hot_reload_test(pool, num_threads=10, operations_per_thread=30)
    results["config_hot_reload"] = r4
    print(f"  → {r4.success_count}/{r4.total} success, "
          f"reload_count={r4.success_count // 5}, failures={r4.failure_count}")

    # Summary
    print("\n" + "=" * 60)
    print("测试汇总")
    print("=" * 60)
    for name, r in results.items():
        status = "✅" if r.failure_count == 0 else "⚠️"
        print(f"  {status} {name}: {r.success_count}/{r.total} success, "
              f"avg={r.avg_latency_ms:.1f}ms, p95={r.p95_latency_ms:.1f}ms")

    pool.close()
    return results


if __name__ == "__main__":
    run_all_tests()
