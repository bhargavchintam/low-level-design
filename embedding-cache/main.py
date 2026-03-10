"""LRU embedding cache with compute-on-miss - the classic memoization pattern, specialized
for embeddings: a miss calls out to an (expensive, simulated) model instead of returning
a sentinel, so the cache is transparent to the caller - get() always returns a vector.
"""

import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Callable

import numpy as np


@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0
    evictions: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total else 0.0


class EmbeddingCache:
    """OrderedDict gives O(1) get/move-to-end/popitem(last=False) for free, which is all
    an LRU needs - no reason to hand-roll a linked list when the stdlib already has one."""

    def __init__(self, capacity: int, compute_fn: Callable[[str], np.ndarray]):
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self.compute_fn = compute_fn
        self._store: OrderedDict[str, np.ndarray] = OrderedDict()
        self.stats = CacheStats()

    def get(self, key: str) -> np.ndarray:
        if key in self._store:
            self.stats.hits += 1
            self._store.move_to_end(key)
            return self._store[key]

        self.stats.misses += 1
        value = self.compute_fn(key)
        self._store[key] = value
        if len(self._store) > self.capacity:
            self._store.popitem(last=False)
            self.stats.evictions += 1
        return value

    def __len__(self):
        return len(self._store)


class FakeEmbeddingModel:
    """Stand-in for a real embedding API call: deterministic per input (so repeated calls
    on the same text return the same vector) but simulates real latency via sleep."""

    def __init__(self, dim: int = 16, latency_s: float = 0.004):
        self.dim = dim
        self.latency_s = latency_s
        self.calls = 0

    def embed(self, text: str) -> np.ndarray:
        self.calls += 1
        time.sleep(self.latency_s)
        rng = np.random.default_rng(abs(hash(text)) % (2**32))
        return rng.normal(size=self.dim)


def zipfian_query_stream(vocab: list[str], n_requests: int, seed: int) -> list[str]:
    """A realistic access pattern: a handful of queries dominate traffic (power law),
    the rest trail off - the shape that makes an LRU cache actually pay off."""
    rng = np.random.default_rng(seed)
    ranks = rng.zipf(a=1.3, size=n_requests)
    return [vocab[(r - 1) % len(vocab)] for r in ranks]


def main():
    vocab = [f"query-{i}" for i in range(60)]
    stream = zipfian_query_stream(vocab, n_requests=400, seed=3)

    model = FakeEmbeddingModel(dim=16, latency_s=0.004)
    cache = EmbeddingCache(capacity=20, compute_fn=model.embed)

    t0 = time.perf_counter()
    for query in stream:
        cache.get(query)
    elapsed = time.perf_counter() - t0

    stats = cache.stats
    print(f"requests={len(stream)}  unique_queries_in_stream={len(set(stream))}  cache_capacity={cache.capacity}")
    print(f"hits={stats.hits}  misses={stats.misses}  evictions={stats.evictions}  hit_rate={stats.hit_rate:.1%}")
    print(f"model.calls={model.calls}  wall_time={elapsed:.3f}s")

    naive_time = len(stream) * model.latency_s
    print(f"\nno-cache baseline would need {len(stream)} model calls (~{naive_time:.3f}s of pure latency); "
          f"cache needed only {model.calls} (~{model.calls * model.latency_s:.3f}s) - "
          f"{(1 - model.calls / len(stream)):.1%} of calls avoided.")

    assert model.calls == stats.misses, "every miss must trigger exactly one compute call, and hits must trigger none"
    assert stats.hits + stats.misses == len(stream)
    assert len(cache) <= cache.capacity
    misses_snapshot, calls_snapshot = stats.misses, model.calls  # freeze before the determinism probe below adds calls

    # determinism check: computing a key outside the cache reproduces whatever the cache is holding for it
    for key in vocab[:3]:
        cached = cache.get(key)
        recomputed = model.embed(key)
        assert np.allclose(cached, recomputed), "embedding for the same key should be deterministic"

    print(f"\nself-check passed: {misses_snapshot} misses == {calls_snapshot} model calls, "
          f"cache never exceeded capacity ({len(cache)}/{cache.capacity}), embeddings are deterministic.")


if __name__ == "__main__":
    main()
