"""KV cache pool - fixed-size page pool shared across sequences, vLLM-style PagedAttention
memory manager. Each sequence's KV cache is a block table (list of page ids) grown one page
at a time as it generates tokens, instead of every sequence pre-reserving worst-case space
up front. When the pool runs out of free pages, the least-recently-touched *evictable*
sequence is evicted wholesale to make room - the trade that lets many sequences share a fixed
GPU memory budget.
"""

from collections import OrderedDict
from dataclasses import dataclass, field


class OutOfPages(Exception):
    pass


class UnknownSequence(Exception):
    pass


@dataclass
class Sequence:
    seq_id: int
    block_table: list[int] = field(default_factory=list)
    num_tokens: int = 0
    evictable: bool = True  # False = currently being generated / pinned, can't be preempted


class PagePool:
    """Owns the raw pages: which are free, which sequence owns each allocated one.
    Knows nothing about block tables or eviction policy - just hands out and reclaims
    single pages and enforces "a page has at most one owner at a time"."""

    def __init__(self, num_pages: int):
        self.num_pages = num_pages
        self._free: list[int] = list(range(num_pages))
        self._owner: dict[int, int] = {}  # page_id -> seq_id

    def free_count(self) -> int:
        return len(self._free)

    def owner_of(self, page_id: int) -> int | None:
        return self._owner.get(page_id)

    def alloc(self, seq_id: int) -> int:
        if not self._free:
            raise OutOfPages("no free pages")
        page_id = self._free.pop()
        self._owner[page_id] = seq_id
        return page_id

    def release(self, page_id: int) -> None:
        assert page_id in self._owner, f"page {page_id} is already free"
        del self._owner[page_id]
        self._free.append(page_id)


class KVCachePool:
    """Manager on top of PagePool: tracks each sequence's block table, grows it on
    demand, and evicts least-recently-touched evictable sequences (LRU order kept in
    an OrderedDict) whenever growth needs more pages than are currently free."""

    def __init__(self, num_pages: int, block_size: int):
        self.pool = PagePool(num_pages)
        self.block_size = block_size
        self._sequences: dict[int, Sequence] = {}
        self._lru: "OrderedDict[int, None]" = OrderedDict()
        self.evictions: list[int] = []

    def new_sequence(self, seq_id: int) -> Sequence:
        if seq_id in self._sequences:
            raise ValueError(f"sequence {seq_id} already exists")
        seq = Sequence(seq_id)
        self._sequences[seq_id] = seq
        self._touch(seq_id)
        return seq

    def _touch(self, seq_id: int):
        self._lru[seq_id] = None
        self._lru.move_to_end(seq_id)

    def set_evictable(self, seq_id: int, evictable: bool):
        self._get(seq_id).evictable = evictable

    def pages_needed(self, seq_id: int, num_tokens: int) -> int:
        seq = self._get(seq_id)
        pages_required = -(-(seq.num_tokens + num_tokens) // self.block_size)  # ceil div
        return max(0, pages_required - len(seq.block_table))

    def grow(self, seq_id: int, num_new_tokens: int) -> list[int]:
        """Appends num_new_tokens of generated tokens to seq_id, allocating whatever
        new pages that requires. Evicts other sequences (LRU among evictable ones,
        never seq_id itself) until enough pages are free, or raises OutOfPages if
        evicting everything evictable still wouldn't be enough."""
        seq = self._get(seq_id)
        needed = self.pages_needed(seq_id, num_new_tokens)

        while self.pool.free_count() < needed:
            victim = self._pick_eviction_victim(exclude=seq_id)
            if victim is None:
                raise OutOfPages(
                    f"sequence {seq_id} needs {needed} pages, only "
                    f"{self.pool.free_count()} free and nothing left evictable"
                )
            self._evict(victim)

        new_pages = [self.pool.alloc(seq_id) for _ in range(needed)]
        seq.block_table.extend(new_pages)
        seq.num_tokens += num_new_tokens
        self._touch(seq_id)
        return new_pages

    def free_sequence(self, seq_id: int):
        seq = self._get(seq_id)
        for page_id in seq.block_table:
            self.pool.release(page_id)
        seq.block_table.clear()
        self._sequences.pop(seq_id)
        self._lru.pop(seq_id, None)

    def _pick_eviction_victim(self, exclude: int) -> int | None:
        for seq_id in self._lru:  # OrderedDict walks least-recently-touched first
            if seq_id != exclude and self._sequences[seq_id].evictable:
                return seq_id
        return None

    def _evict(self, seq_id: int):
        self.free_sequence(seq_id)
        self.evictions.append(seq_id)

    def _get(self, seq_id: int) -> Sequence:
        if seq_id not in self._sequences:
            raise UnknownSequence(seq_id)
        return self._sequences[seq_id]

    def block_table_of(self, seq_id: int) -> list[int]:
        return list(self._get(seq_id).block_table)

    def live_sequences(self) -> list[int]:
        return list(self._sequences.keys())


def main():
    cache = KVCachePool(num_pages=8, block_size=4)

    print("prompt-fill: A, B, C each get an 8-token prompt (2 pages each, 8 pages total):")
    for seq_id, tokens in [("A", 8), ("B", 8), ("C", 8)]:
        cache.new_sequence(seq_id)
        pages = cache.grow(seq_id, tokens)
        print(f"  {seq_id}: +{tokens} tokens -> pages {pages}, free={cache.pool.free_count()}")

    print("\nA decodes 4 more tokens (needs 1 more page, fits in the 2 still free):")
    pages = cache.grow("A", 4)
    print(f"  A: +4 tokens -> pages {pages}, free={cache.pool.free_count()}  (A block table: {cache.block_table_of('A')})")

    # B is "still actively generating" - not a valid eviction target even though
    # it's the least-recently-touched sequence at this point.
    cache.set_evictable("B", False)
    c_pages_before_eviction = cache.block_table_of("C")
    print(f"\nB pinned as non-evictable (still generating). C's pages before eviction: {c_pages_before_eviction}")

    print("\nnew sequence D needs an 8-token prompt (2 pages) but only 1 page is free - "
          "must evict. LRU order skips pinned B, so C (next LRU) is evicted instead:")
    cache.new_sequence("D")
    d_pages = cache.grow("D", 8)
    print(f"  evicted: {cache.evictions}")
    print(f"  D: +8 tokens -> pages {d_pages}, free={cache.pool.free_count()}")

    print(f"\nlive sequences: {cache.live_sequences()}")
    for seq_id in cache.live_sequences():
        print(f"  {seq_id}: block_table={cache.block_table_of(seq_id)}")

    # --- invariants ---
    live = cache.live_sequences()
    all_owned_pages = [p for seq_id in live for p in cache.block_table_of(seq_id)]

    assert cache.evictions == ["C"], f"expected only C to be evicted, got {cache.evictions}"
    assert "C" not in live, "evicted sequence must no longer be live"
    assert "B" in live, "pinned (non-evictable) sequence must never be evicted"

    # No page double-booked across two sequences' block tables.
    assert len(all_owned_pages) == len(set(all_owned_pages)), "a page is owned by more than one sequence"

    # Every page a sequence claims must agree with the pool's own owner record.
    for seq_id in live:
        for p in cache.block_table_of(seq_id):
            assert cache.pool.owner_of(p) == seq_id, f"page {p} owner mismatch for {seq_id}"

    # Conservation: free pages + allocated pages must always equal total capacity.
    assert cache.pool.free_count() + len(all_owned_pages) == cache.pool.num_pages

    # C's evicted pages must have been immediately reusable - D's new pages should
    # be drawn from exactly the pages C just gave back (proves release() -> alloc()
    # round-trips real capacity, not just bookkeeping).
    assert set(d_pages) <= set(c_pages_before_eviction), \
        f"D's pages {d_pages} should be reused from C's freed pages {c_pages_before_eviction}"

    print(f"\nself-check passed: no double-booked pages, pool bookkeeping matches every "
          f"block table, capacity conserved ({cache.pool.free_count()} free + "
          f"{len(all_owned_pages)} allocated = {cache.pool.num_pages}), and D reused C's "
          f"freed pages directly.")


if __name__ == "__main__":
    main()
