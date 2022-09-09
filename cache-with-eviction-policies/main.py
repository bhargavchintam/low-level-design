"""Cache with pluggable eviction policies - Strategy pattern.

Cache owns capacity + storage and only ever asks its EvictionPolicy which
key to drop; it has no idea whether that policy is LRU, LFU, FIFO or random.
"""

from abc import ABC, abstractmethod
from collections import OrderedDict, deque
from enum import Enum
import random


class PolicyType(Enum):
    LRU = "LRU"
    LFU = "LFU"
    FIFO = "FIFO"
    RANDOM = "RANDOM"


class EvictionPolicy(ABC):
    """Contract a Cache delegates all eviction bookkeeping to."""

    @abstractmethod
    def on_insert(self, key: str) -> None:
        """A brand new key was added to the cache."""

    @abstractmethod
    def on_access(self, key: str) -> None:
        """An existing key was read or overwritten (cache hit)."""

    @abstractmethod
    def evict(self) -> str:
        """Pick a key to remove, drop it from internal bookkeeping, and return it."""


class LRUPolicy(EvictionPolicy):
    """Evicts the least recently used key. Recency tracked via an OrderedDict."""

    def __init__(self):
        self._order: "OrderedDict[str, None]" = OrderedDict()

    def on_insert(self, key: str) -> None:
        self._order[key] = None

    def on_access(self, key: str) -> None:
        self._order.move_to_end(key)

    def evict(self) -> str:
        key, _ = self._order.popitem(last=False)
        return key


class LFUPolicy(EvictionPolicy):
    """Evicts the least frequently used key; ties broken by earliest insertion."""

    def __init__(self):
        self._freq: dict[str, int] = {}

    def on_insert(self, key: str) -> None:
        self._freq[key] = 1

    def on_access(self, key: str) -> None:
        self._freq[key] += 1

    def evict(self) -> str:
        # min() over a dict scans in insertion order and only replaces on a
        # strictly smaller value, so ties resolve to the earliest-inserted key.
        key = min(self._freq, key=self._freq.get)
        del self._freq[key]
        return key


class FIFOPolicy(EvictionPolicy):
    """Evicts in strict insertion order; accesses never change the order."""

    def __init__(self):
        self._queue: "deque[str]" = deque()

    def on_insert(self, key: str) -> None:
        self._queue.append(key)

    def on_access(self, key: str) -> None:
        pass

    def evict(self) -> str:
        return self._queue.popleft()


class RandomPolicy(EvictionPolicy):
    """Evicts a uniformly random key among those currently cached."""

    def __init__(self, rng: random.Random | None = None):
        self._keys: set[str] = set()
        self._rng = rng or random.Random()

    def on_insert(self, key: str) -> None:
        self._keys.add(key)

    def on_access(self, key: str) -> None:
        pass

    def evict(self) -> str:
        key = self._rng.choice(sorted(self._keys))
        self._keys.discard(key)
        return key


class Cache:
    """Fixed-capacity key/value store. Doesn't know which eviction strategy
    it's running - that decision is entirely delegated to `policy`."""

    def __init__(self, capacity: int, policy: EvictionPolicy):
        self.capacity = capacity
        self.policy = policy
        self._store: dict[str, int] = {}

    def get(self, key: str):
        if key not in self._store:
            return None
        self.policy.on_access(key)
        return self._store[key]

    def put(self, key: str, value: int) -> str | None:
        """Inserts/updates `key`. Returns the evicted key, if a slot had to be freed."""
        if key in self._store:
            self._store[key] = value
            self.policy.on_access(key)
            return None

        evicted = None
        if len(self._store) >= self.capacity:
            evicted = self.policy.evict()
            del self._store[evicted]

        self._store[key] = value
        self.policy.on_insert(key)
        return evicted


# Same op sequence replayed against every policy so the eviction differences
# are directly comparable. Capacity is 3, so the 4th and 6th puts must evict.
OPS = [
    ("put", "A", 1),
    ("put", "B", 2),
    ("put", "C", 3),
    ("get", "A", None),
    ("get", "B", None),
    ("get", "A", None),
    ("put", "D", 4),
    ("get", "C", None),
    ("put", "E", 5),
]


def make_policy(kind: PolicyType) -> EvictionPolicy:
    if kind is PolicyType.LRU:
        return LRUPolicy()
    if kind is PolicyType.LFU:
        return LFUPolicy()
    if kind is PolicyType.FIFO:
        return FIFOPolicy()
    return RandomPolicy(random.Random(42))  # seeded so the demo is reproducible


def run_demo(kind: PolicyType) -> list[str]:
    print(f"\n--- {kind.value} ---")
    cache = Cache(capacity=3, policy=make_policy(kind))
    evictions = []
    for op, key, value in OPS:
        if op == "put":
            evicted = cache.put(key, value)
            if evicted:
                evictions.append(evicted)
                print(f"put {key}={value:<3} -> evicted {evicted!r}")
            else:
                print(f"put {key}={value}")
        else:
            result = cache.get(key)
            outcome = f"HIT {result}" if result is not None else "MISS"
            print(f"get {key}     -> {outcome}")
    return evictions


def main():
    results = {}
    for kind in PolicyType:
        results[kind.value] = run_demo(kind)

    print("\n--- side-by-side eviction comparison ---")
    for name, evicted in results.items():
        print(f"{name:<6} evicted: {evicted}")


if __name__ == "__main__":
    main()
