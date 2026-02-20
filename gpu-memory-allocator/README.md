# GPU Memory Allocator

## Problem
Design the allocator that sits underneath `cudaMalloc` / a PyTorch caching
allocator: a flat device memory pool that hands out byte offsets on request
and takes them back in any order, while trying to keep fragmentation low so a
later large allocation doesn't fail just because free bytes exist but aren't
contiguous.

## Design
- `Allocator` (ABC) - `alloc(size) -> offset`, `free(offset)`, `free_bytes()`,
  `largest_free_block()`, plus a derived `fragmentation()` (`1 -
  largest_free_block / free_bytes`). Any workload driver runs unmodified
  against either implementation.
- `BestFitAllocator` - a free list of `(offset, size)` blocks. `alloc` scans
  for the smallest block that still fits (least leftover sliver) and splits
  it if there's leftover; `free` reinserts and immediately coalesces with
  adjacent free neighbors. Fine-grained, but a freed block only recovers
  contiguity if its neighbors happen to also be free.
- `BuddyAllocator` - pool size is a power of two, tracked as free lists per
  level (level 0 = whole pool, each level down is half its parent's size).
  `alloc` rounds the request up to a power of two and recursively splits a
  bigger free block into buddy halves until one of the right size exists.
  `free` walks back up, merging with the buddy whenever it's also free - a
  block's buddy is always at a fixed, XOR-computable offset, which is why
  buddy systems don't accumulate the permanent slivers a naive free list
  does, at the cost of rounding-up waste.
- `run_workload` - allocates a batch of tensor-shaped (non-round) sizes, then
  frees them back in a scrambled order, sampling fragmentation and largest
  free block after every free.

## Patterns used
- **Strategy** - `Allocator` is the swappable placement/coalescing policy;
  the workload driver and demo don't know which one they're running against.

## How to run
```
cd /Users/bhargav/Desktop/low-level-design/gpu-memory-allocator
python3 main.py
```
