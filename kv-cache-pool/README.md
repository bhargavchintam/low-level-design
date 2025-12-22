# KV Cache Pool

## Problem
Design the memory manager behind vLLM-style PagedAttention: a fixed pool of
GPU pages shared across many in-flight sequences. Each sequence's KV cache
grows page-by-page as it generates tokens instead of reserving worst-case
space up front; when the pool is full, some sequence has to be evicted
wholesale to make room - but never one that's actively being decoded right
now.

## Design
- `PagePool` - the raw resource: a free list plus a `page_id -> seq_id`
  owner map. Only responsibility is "hand out a free page" / "reclaim a page"
  while guaranteeing a page never has two owners at once.
- `Sequence` - `seq_id`, its `block_table` (ordered list of page ids), token
  count, and an `evictable` flag (`False` while it's pinned / mid-generation).
- `KVCachePool` - the manager. `grow(seq_id, num_new_tokens)` computes how
  many additional pages the new tokens require (`ceil(total_tokens /
  block_size) - len(block_table)`), evicts LRU-among-evictable sequences
  (never the caller itself) until enough pages are free, then allocates and
  appends. `free_sequence` releases every page in a block table back to the
  pool at once. LRU order is tracked with an `OrderedDict` touched on every
  create/grow.
- Demo: three sequences fill the pool with prompts, one keeps decoding and
  needs one more page, then a fourth sequence's prompt needs 2 pages with
  only 1 free. The least-recently-touched sequence is pinned non-evictable
  (simulating "still generating"), so eviction correctly skips it and takes
  the next-LRU sequence instead.

## Patterns used
- Resource pool - `PagePool` is a fixed-capacity pool of interchangeable
  units (pages) with acquire/release, the same shape as a connection or
  thread pool.
- LRU eviction (Strategy-shaped) - eviction victim selection is a single
  method (`_pick_eviction_victim`) walking one ordered structure, so a
  different policy (LFU, cost-aware, etc.) would only mean swapping that one
  method out.

## How to run
```
cd /Users/bhargav/Desktop/low-level-design/kv-cache-pool
python3 main.py
```
