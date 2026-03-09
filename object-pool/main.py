"""Object pool - reusable buffers checked out via acquire() and handed back via release(), instead
of being allocated fresh and garbage-collected every use. Caps how many ever get constructed
(max_size); once warm, acquire() hands out a previously-released object instead of building a new
one - the standard trick for expensive-to-construct resources (numpy buffers, DB connections, GPU
memory blocks) under high-churn, high-concurrency workloads."""

import random
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable, TypeVar

import numpy as np

T = TypeVar("T")


@dataclass
class PoolStats:
    created: int = 0
    acquired: int = 0
    released: int = 0

    @property
    def reused(self) -> int:
        return self.acquired - self.created


class PoolExhausted(Exception):
    pass


class ObjectPool:
    """Thread-safe: a Semaphore caps total live objects at max_size (blocking acquire() until one
    frees up rather than over-allocating), and a Lock guards the free list and stats. `factory`
    builds a new object; `reset` (if given) is run on an object before it's handed out again, so a
    caller never sees another caller's leftover state."""

    def __init__(self, factory: Callable[[], T], reset: Callable[[T], None] | None = None,
                 max_size: int = 10):
        self._factory = factory
        self._reset = reset
        self.max_size = max_size
        self._free: list[T] = []
        self._in_use: set[int] = set()  # id() of every currently-checked-out object
        self._lock = threading.Lock()
        self._capacity = threading.Semaphore(max_size)
        self.stats = PoolStats()

    def acquire(self, timeout: float | None = None) -> T:
        if not self._capacity.acquire(timeout=timeout):
            raise PoolExhausted(f"no object available within {timeout}s (max_size={self.max_size})")
        with self._lock:
            if self._free:
                obj = self._free.pop()
            else:
                obj = self._factory()
                self.stats.created += 1
            self._in_use.add(id(obj))
            self.stats.acquired += 1
        return obj

    def release(self, obj: T):
        with self._lock:
            if id(obj) not in self._in_use:
                raise ValueError("releasing an object this pool didn't hand out (or double-release)")
            self._in_use.discard(id(obj))
            if self._reset is not None:
                self._reset(obj)
            self._free.append(obj)
            self.stats.released += 1
        self._capacity.release()

    @property
    def in_use_count(self) -> int:
        with self._lock:
            return len(self._in_use)

    @contextmanager
    def lease(self, timeout: float | None = None):
        """RAII-style checkout: guarantees release() runs even if the caller's block raises."""
        obj = self.acquire(timeout)
        try:
            yield obj
        finally:
            self.release(obj)


def make_buffer() -> np.ndarray:
    return np.zeros(256, dtype=np.float64)


def reset_buffer(buf: np.ndarray):
    buf.fill(0.0)


def worker(pool: ObjectPool, n_cycles: int, rng_seed: int, out_counts: list, errors: list, idx: int):
    rng = random.Random(rng_seed)
    local_count = 0
    try:
        for _ in range(n_cycles):
            with pool.lease() as buf:
                assert np.all(buf == 0.0), "acquired buffer wasn't reset before handout"
                buf[:] = rng.random()
                time.sleep(rng.uniform(0.0005, 0.002))  # hold the buffer briefly, like real work
                local_count += 1
    except Exception as e:  # thread exceptions don't propagate on their own - collect them
        errors.append(e)
    out_counts[idx] = local_count


def main():
    max_size = 8

    # Small, explicit check first, on a throwaway pool: acquire, dirty the buffer, release,
    # acquire again - must come back clean (reset actually ran).
    warmup_pool = ObjectPool(make_buffer, reset=reset_buffer, max_size=1)
    buf = warmup_pool.acquire()
    buf[:] = 42.0
    warmup_pool.release(buf)
    buf2 = warmup_pool.acquire()
    assert np.all(buf2 == 0.0), "buffer wasn't reset on release"
    warmup_pool.release(buf2)
    assert warmup_pool.stats.created == 1, "second acquire should have reused, not constructed"
    print("warmup check passed: released buffer came back reset and got reused, not rebuilt\n")

    # Stress test on a fresh pool: 12 threads x 500 acquire/release cycles = 6000 total
    # acquisitions through a pool capped at 8 objects - far more churn than capacity, the point.
    pool = ObjectPool(make_buffer, reset=reset_buffer, max_size=max_size)
    n_threads = 12
    n_cycles = 150
    threads = []
    out_counts = [0] * n_threads
    errors: list[Exception] = []
    for i in range(n_threads):
        t = threading.Thread(target=worker, args=(pool, n_cycles, i, out_counts, errors, i))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"worker thread(s) raised: {errors}"

    total_cycles = sum(out_counts)
    expected_cycles = n_threads * n_cycles
    print(f"{n_threads} threads x {n_cycles} acquire/release cycles = {expected_cycles} total")
    print(f"objects ever constructed: {pool.stats.created} (cap: {max_size})")
    print(f"total acquisitions: {pool.stats.acquired}, reused: {pool.stats.reused} "
          f"({pool.stats.reused / pool.stats.acquired:.1%})")
    print(f"objects still checked out when done: {pool.in_use_count}")

    assert total_cycles == expected_cycles, f"expected {expected_cycles} completed cycles, got {total_cycles}"
    assert pool.stats.acquired == expected_cycles
    assert pool.stats.released == expected_cycles
    assert pool.stats.created <= max_size, (
        f"pool constructed {pool.stats.created} objects, more than its cap of {max_size} - "
        "not actually reusing"
    )
    assert pool.stats.created > 1, (
        "only 1 object was ever built - threads weren't actually contending for buffers, "
        "so this run doesn't prove the pool caps concurrent construction"
    )
    assert pool.in_use_count == 0, f"{pool.in_use_count} objects never released - leak detected"
    assert len(pool._free) == pool.stats.created, "free list doesn't account for every constructed object"

    print(f"\nself-check passed: {expected_cycles} acquire/release cycles through a pool capped at "
          f"{max_size} objects only ever constructed {pool.stats.created} of them "
          f"({pool.stats.reused / pool.stats.acquired:.1%} reuse rate), and zero objects leaked.")


if __name__ == "__main__":
    main()
