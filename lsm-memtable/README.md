# LSM Memtable

## Problem
Design the write/read path of an LSM-tree-style store: writes go to a fast in-memory structure,
which periodically flushes to immutable on-disk-style runs instead of updating data in place. Reads
must transparently merge across the memtable and every flushed run, always returning the *newest*
version of a key, and deletes must be able to shadow older data (a tombstone) without the store
needing to touch or rewrite the older run it's shadowing.

## Design
- `Memtable` - mutable, kept sorted by key via `bisect.insort` on first write to a key, so a flush
  can hand its contents to an `SSTable` already sorted. `delete(key)` is just `put(key, TOMBSTONE)`.
- `SSTable` - immutable sorted run built once from a flushed memtable's entries; `get(key)` does a
  binary search (`bisect_left`) over its sorted keys.
- `LSMTree` - facade over one active `Memtable` and a list of `SSTable` runs (oldest first).
  `put`/`delete` write to the memtable and auto-`flush()` once it crosses `flush_threshold`
  entries. `get(key)` checks the memtable first, then walks runs *newest to oldest*, returning the
  first match (a tombstone found this way still means "deleted" - a `TOMBSTONE` maps to `None`,
  same as a key that was never written). `compact()` k-way-merges every run (oldest to newest, each
  overwriting the last so newer values win) into one new run and drops tombstones entirely, since
  once there's no older data left underneath a delete, there's nothing left to shadow.

## Patterns used
- **Facade** - `LSMTree` hides the memtable/multi-run merge logic behind four methods
  (`put`/`delete`/`get`/`flush`/`compact`); callers never touch a `Memtable` or `SSTable` directly.

## How to run
```
cd /Users/bhargav/Desktop/low-level-design/lsm-memtable
python3 main.py
```
The demo runs 63 puts/overwrites/deletes/resurrections (a key deleted then written again must come
back) through an `LSMTree` with `flush_threshold=8`, producing 8 flushed `SSTable` runs. Every op is
mirrored onto a plain-dict reference model, and every key's `lsm.get()` is asserted to match the
reference both before and after `compact()`. It also confirms compaction actually merges down to
one run and that deleted keys leave zero trace in the compacted run (space genuinely reclaimed, not
just shadowed).
