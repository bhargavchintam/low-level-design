# Embedding Cache

## Problem
Build an LRU cache for embeddings where a cache miss transparently computes
the value via a callback (an expensive model call) instead of returning a
sentinel - callers always just get a vector back. Track hit/miss stats to
show the cache is actually paying for itself.

## Design
- `EmbeddingCache` - `OrderedDict` gives O(1) `get` / `move_to_end` /
  `popitem(last=False)`, which is everything an LRU needs; no reason to
  hand-roll a linked list a second time in this repo (see `lru-cache/`)
  when the stdlib already provides one. `get(key)` returns the cached vector
  on a hit (and refreshes recency), or calls `compute_fn(key)` on a miss,
  stores the result, and evicts the least-recently-used entry if now over
  capacity.
- `CacheStats` - hits, misses, evictions, and a derived `hit_rate`.
- `FakeEmbeddingModel` - stands in for a real embedding API: deterministic
  per input (repeated calls on the same text return the same vector) but
  sleeps to simulate real latency, and counts its own calls.
- `zipfian_query_stream` - generates a power-law access pattern (a few
  queries dominate traffic), the realistic shape that makes an LRU cache
  worth having; uniform random traffic wouldn't show a meaningful hit rate.

## Patterns used
- **Memoization / compute-on-miss** - the cache's `get` is the only entry
  point; whether a value came from the store or from `compute_fn` is
  invisible to the caller.

## How to run
```
cd /Users/bhargav/Desktop/low-level-design/embedding-cache
python3 main.py
```
The demo replays 400 Zipfian-distributed queries over 60 possible texts
through a capacity-20 cache, reports hit/miss/eviction stats and time saved
vs. no caching, and asserts `model.calls == stats.misses` (every miss
computes exactly once, every hit computes zero times).
