# Object Pool

## Problem
Design a pool of reusable, expensive-to-construct objects (buffers, connections, GPU memory
blocks) that hands them out to callers and takes them back, reusing freed objects instead of
constructing new ones on every request, while capping how many ever exist concurrently and never
leaking one that a caller forgot to release.

## Design
- `ObjectPool` - `factory` builds a new object, `reset` (optional) clears one before it's handed
  out again, `max_size` caps how many are ever alive. A `threading.Semaphore(max_size)` blocks
  `acquire()` when the pool is at capacity instead of over-allocating; a `Lock` guards the free
  list, the `_in_use` id-set, and `PoolStats`. `acquire()` pops from the free list if anything's
  there, otherwise calls `factory()` (only then does `stats.created` go up). `release(obj)` runs
  `reset`, pushes the object back onto the free list, and releases the semaphore slot.
- `PoolStats` - `created`, `acquired`, `released`, and a derived `reused = acquired - created`.
- `lease()` - a `@contextmanager` wrapping acquire/release so `with pool.lease() as buf:` always
  releases, even if the block raises - the same guarantee `experiment-tracker`'s `RunContext`
  gives a run's lifecycle.

## Patterns used
- **Object Pool** - reusable instances are checked out and returned instead of being constructed
  and garbage-collected per use, trading a bounded amount of held memory for avoiding repeated
  expensive construction.
- **Context Manager (RAII)** - `lease()` ties an object's checkout to a `with` block's lifetime so
  release is never forgotten, mirroring how a file handle or lock guarantees its own cleanup.

## How to run
```
cd /Users/bhargav/Desktop/low-level-design/object-pool
python3 main.py
```
The demo pools 256-element numpy buffers capped at 8. A warmup check confirms a released buffer
comes back zeroed (reset actually ran) and reused rather than rebuilt. Then 12 real threads each
run 150 acquire/hold/release cycles (1,800 total, well beyond the cap) with a small sleep while
holding the buffer to force genuine contention. It asserts every cycle completed, the pool never
constructed more than 8 objects, it constructed *more than 1* (proving threads really contended for
buffers rather than trivially serializing), and zero objects remain checked out when done - reuse
and no leaks, both proven under real concurrency rather than a single-threaded loop.
