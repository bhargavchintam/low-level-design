"""GPU memory allocator demo - best-fit and buddy allocators behind a common Allocator interface.

Simulates a flat device memory pool (what sits underneath cudaMalloc / a PyTorch caching
allocator): callers ask for byte offsets, get back a handle, and free them in any order.
BestFitAllocator hunts its free list for the smallest block that still fits (fine-grained,
but frees can leave permanent slivers no future request is ever small enough to reuse well).
BuddyAllocator only ever splits/merges power-of-two blocks, so a freed block always has a
well-defined buddy to try merging with - fragmentation-resistant, at the cost of internal
waste from rounding every request up to a power of two.
"""

import numpy as np
from abc import ABC, abstractmethod
from dataclasses import dataclass


class OutOfMemory(Exception):
    pass


@dataclass(frozen=True)
class Block:
    offset: int
    size: int


class Allocator(ABC):
    """Contract a workload driver can run against either implementation unmodified."""

    @abstractmethod
    def alloc(self, size: int) -> int:
        """Returns the offset of a block >= size bytes. Raises OutOfMemory if none fits."""

    @abstractmethod
    def free(self, offset: int) -> None:
        ...

    @abstractmethod
    def free_bytes(self) -> int:
        ...

    @abstractmethod
    def largest_free_block(self) -> int:
        ...

    def fragmentation(self) -> float:
        """0.0 = all free memory is in one contiguous block, ~1.0 = free memory is
        scattered into many blocks too small to individually serve a large request."""
        free = self.free_bytes()
        if free == 0:
            return 0.0
        return 1.0 - self.largest_free_block() / free


class BestFitAllocator(Allocator):
    """Free list of (offset, size) blocks. alloc() scans for the smallest block that
    still fits the request (least leftover sliver) and splits it if there's leftover.
    free() reinserts and immediately coalesces with adjacent free neighbors, so a freed
    block only stays fragmented if its neighbors are still allocated."""

    def __init__(self, pool_size: int):
        self.pool_size = pool_size
        self._free: list[Block] = [Block(0, pool_size)]
        self._allocated: dict[int, int] = {}  # offset -> size

    def alloc(self, size: int) -> int:
        candidates = [b for b in self._free if b.size >= size]
        if not candidates:
            raise OutOfMemory(f"no free block >= {size}B (largest free = {self.largest_free_block()}B)")
        best = min(candidates, key=lambda b: b.size)
        self._free.remove(best)
        if best.size > size:
            self._free.append(Block(best.offset + size, best.size - size))
        self._allocated[best.offset] = size
        return best.offset

    def free(self, offset: int) -> None:
        size = self._allocated.pop(offset)
        self._free.append(Block(offset, size))
        self._coalesce()

    def _coalesce(self):
        self._free.sort(key=lambda b: b.offset)
        merged: list[Block] = []
        for b in self._free:
            if merged and merged[-1].offset + merged[-1].size == b.offset:
                merged[-1] = Block(merged[-1].offset, merged[-1].size + b.size)
            else:
                merged.append(b)
        self._free = merged

    def free_bytes(self) -> int:
        return sum(b.size for b in self._free)

    def largest_free_block(self) -> int:
        return max((b.size for b in self._free), default=0)


class BuddyAllocator(Allocator):
    """pool_size must be a power of two. Free blocks are tracked per level (level 0 is
    the whole pool, each level down is half the block size of its parent). alloc() rounds
    the request up to a power of two, finds the smallest free level that can serve it, and
    recursively splits bigger blocks into "buddy" halves until one of the right size exists.
    free() walks back up merging with the buddy whenever it's also free - a block's buddy
    is always at a fixed, computable offset (XOR with the block size), which is the whole
    trick and the reason buddy systems don't accumulate the slivers best-fit does."""

    def __init__(self, pool_size: int):
        assert pool_size & (pool_size - 1) == 0, "pool_size must be a power of two"
        self.pool_size = pool_size
        self.max_level = pool_size.bit_length() - 1
        self._free_lists: dict[int, set[int]] = {lvl: set() for lvl in range(self.max_level + 1)}
        self._free_lists[0].add(0)
        self._allocated: dict[int, int] = {}  # offset -> level

    def _level_size(self, level: int) -> int:
        return self.pool_size >> level

    def _level_for(self, size: int) -> int:
        level = self.max_level
        while level > 0 and self._level_size(level - 1) >= size:
            level -= 1
        return level

    def _buddy_offset(self, offset: int, level: int) -> int:
        return offset ^ self._level_size(level)

    def alloc(self, size: int) -> int:
        target_level = self._level_for(size)
        level = target_level
        while level >= 0 and not self._free_lists[level]:
            level -= 1
        if level < 0:
            raise OutOfMemory(f"no free block >= {size}B (largest free = {self.largest_free_block()}B)")

        offset = min(self._free_lists[level])
        self._free_lists[level].remove(offset)
        while level < target_level:  # split down to the target size, banking each buddy half
            level += 1
            self._free_lists[level].add(offset + self._level_size(level))
        self._allocated[offset] = target_level
        return offset

    def free(self, offset: int) -> None:
        level = self._allocated.pop(offset)
        while level > 0:
            buddy = self._buddy_offset(offset, level)
            if buddy not in self._free_lists[level]:
                break
            self._free_lists[level].remove(buddy)
            offset = min(offset, buddy)
            level -= 1
        self._free_lists[level].add(offset)

    def free_bytes(self) -> int:
        return sum(self._level_size(lvl) * len(offsets) for lvl, offsets in self._free_lists.items())

    def largest_free_block(self) -> int:
        for level in range(self.max_level + 1):
            if self._free_lists[level]:
                return self._level_size(level)
        return 0


def run_workload(alloc: Allocator, sizes: list[int], free_order: list[int]) -> list[tuple[float, int]]:
    """Allocates every size in order, then frees them back in `free_order` (indices into
    the alloc list). Returns (fragmentation, largest_free_block) sampled after every free,
    so a caller can see whether frees are actually recovering contiguous space or just
    leaving holes - snapshotting here (not after the fact) is what makes it a trace."""
    handles = [alloc.alloc(s) for s in sizes]
    trace = []
    for idx in free_order:
        alloc.free(handles[idx])
        trace.append((alloc.fragmentation(), alloc.largest_free_block()))
    return trace


def main():
    pool_size = 1 << 20  # 1 MiB pretend GPU pool
    rng = np.random.default_rng(3)
    # Tensor-shaped allocation sizes (activations, weight shards, ...), not round numbers -
    # exactly the pattern that stresses a free-list allocator into fragmenting.
    sizes = [int(s) for s in rng.integers(20_000, 140_000, size=10)]
    print(f"pool size: {pool_size:,}B, requests: {sizes}")

    best_fit = BestFitAllocator(pool_size)
    buddy = BuddyAllocator(pool_size)

    # Free out of order and leave gaps between still-live blocks - the scenario where
    # best-fit's lack of coalescing-by-construction actually shows up.
    free_order = [1, 3, 5, 0, 7, 2, 8, 4, 9, 6]

    print("\n--- best-fit ---")
    bf_trace = run_workload(best_fit, sizes, free_order)
    for i, (frag, largest) in zip(free_order, bf_trace):
        print(f"  freed alloc#{i:<2} ({sizes[i]:>7,}B)  fragmentation={frag:.3f}  largest_free={largest:>8,}B")

    print("\n--- buddy ---")
    buddy_trace = run_workload(buddy, sizes, free_order)
    for i, (frag, largest) in zip(free_order, buddy_trace):
        print(f"  freed alloc#{i:<2} ({sizes[i]:>7,}B)  fragmentation={frag:.3f}  largest_free={largest:>8,}B")

    print(f"\nafter freeing everything: best_fit largest_free={best_fit.largest_free_block():,}B "
          f"(pool={pool_size:,}B), buddy largest_free={buddy.largest_free_block():,}B")

    # Both allocators must fully recover the pool once every block is freed - the
    # invariant that actually matters: coalescing/merging isn't leaking capacity.
    assert best_fit.free_bytes() == pool_size and best_fit.largest_free_block() == pool_size
    assert buddy.free_bytes() == pool_size and buddy.largest_free_block() == pool_size

    # Once everything is freed, fragmentation must read exactly 0.0 for both -
    # a single free block spanning the pool is the only way that's possible.
    assert bf_trace[-1][0] == 0.0 and buddy_trace[-1][0] == 0.0
    print("\nself-check passed: both allocators fully coalesce back to one free block "
          "spanning the whole pool after every allocation is freed.")


if __name__ == "__main__":
    main()
