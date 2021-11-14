# Cache with Eviction Policies

## Problem
Design a fixed-capacity cache that, once full, must decide which entry to remove before accepting a new one. The eviction rule (least-recently-used, least-frequently-used, first-in-first-out, random) needs to be swappable without changing the cache's own get/put logic.

## Design
- `EvictionPolicy` (ABC) - `on_insert(key)`, `on_access(key)`, `evict() -> key`. Every strategy implements this and owns its own bookkeeping.
- `LRUPolicy` - tracks recency with an `OrderedDict`; access moves a key to the end, eviction pops from the front.
- `LFUPolicy` - tracks a hit count per key; evicts the lowest count, ties broken by earliest insertion.
- `FIFOPolicy` - a plain queue of insertion order; accesses are ignored entirely.
- `RandomPolicy` - evicts a uniformly random key from the current key set (seeded `random.Random` for a reproducible demo).
- `Cache` - holds `capacity` and the actual `{key: value}` storage. On a full `put`, it asks `policy.evict()` for a key, removes it, then tells the policy about the new key via `on_insert`. `Cache` never branches on which policy it holds.
- `PolicyType` (Enum) - the fixed set of policy kinds, used to drive the demo.

## Patterns used
- **Strategy** - `EvictionPolicy` is the interchangeable algorithm; `Cache` is the context that delegates every eviction decision to whichever policy it was constructed with, entirely via composition.

## How to run
```
cd /Users/bhargav/Desktop/low-level-design/cache-with-eviction-policies
python3 main.py
```
