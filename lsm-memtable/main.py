"""LSM-tree-style storage - writes land in an in-memory sorted memtable; once it crosses a size
threshold it's flushed as an immutable sorted run (an SSTable) and a fresh memtable takes over.
Reads check the memtable first, then runs newest-to-oldest, so a more recent write (or a delete
tombstone) shadows older data for that key without ever mutating it in place. compact() merges all
runs into one, at which point tombstones and shadowed values can finally be dropped for good -
the same write-never-in-place design real LSM engines (LevelDB, RocksDB, Cassandra) use."""

import bisect
from typing import Any

_MISSING = object()  # "no entry at all", distinct from a real stored value of None
TOMBSTONE = object()  # "this key was explicitly deleted"


class Memtable:
    """Mutable, kept sorted by key at all times via bisect.insort on first write, so a flush can
    hand its contents to an SSTable already in sorted order - no separate sort step needed."""

    def __init__(self):
        self._data: dict[str, Any] = {}
        self._sorted_keys: list[str] = []

    def put(self, key: str, value: Any):
        if key not in self._data:
            bisect.insort(self._sorted_keys, key)
        self._data[key] = value

    def delete(self, key: str):
        self.put(key, TOMBSTONE)

    def get(self, key: str) -> Any:
        return self._data.get(key, _MISSING)

    def items(self) -> list[tuple[str, Any]]:
        return [(k, self._data[k]) for k in self._sorted_keys]

    def __len__(self) -> int:
        return len(self._sorted_keys)


class SSTable:
    """Immutable sorted run, built once from a flushed memtable's entries. `seq` is a monotonic
    creation order used to break ties across runs (higher seq = newer = wins)."""

    def __init__(self, entries: list[tuple[str, Any]], seq: int):
        self._keys = [k for k, _ in entries]
        self._values = dict(entries)
        self.seq = seq

    def get(self, key: str) -> Any:
        idx = bisect.bisect_left(self._keys, key)
        if idx < len(self._keys) and self._keys[idx] == key:
            return self._values[key]
        return _MISSING

    def entries(self) -> list[tuple[str, Any]]:
        return [(k, self._values[k]) for k in self._keys]

    def __len__(self) -> int:
        return len(self._keys)


class LSMTree:
    """Facade over one mutable Memtable and zero-or-more immutable SSTables: callers just see
    put/delete/get/flush/compact and never touch a run directly."""

    def __init__(self, flush_threshold: int = 100):
        self.flush_threshold = flush_threshold
        self.memtable = Memtable()
        self.runs: list[SSTable] = []  # oldest first
        self._next_seq = 0
        self.flush_count = 0

    def put(self, key: str, value: Any):
        self.memtable.put(key, value)
        if len(self.memtable) >= self.flush_threshold:
            self.flush()

    def delete(self, key: str):
        self.memtable.delete(key)
        if len(self.memtable) >= self.flush_threshold:
            self.flush()

    def flush(self):
        if len(self.memtable) == 0:
            return
        self.runs.append(SSTable(self.memtable.items(), seq=self._next_seq))
        self._next_seq += 1
        self.flush_count += 1
        self.memtable = Memtable()

    def get(self, key: str) -> Any:
        value = self.memtable.get(key)
        if value is _MISSING:
            for run in reversed(self.runs):  # newest first
                value = run.get(key)
                if value is not _MISSING:
                    break
        return None if value is TOMBSTONE else (None if value is _MISSING else value)

    def compact(self):
        """K-way merge of every run (oldest to newest, each overwriting the last) into a single
        new run, dropping tombstones - once there's no older data left underneath, a delete no
        longer needs a marker, it can just be absent."""
        merged: dict[str, Any] = {}
        for run in self.runs:
            merged.update(run.entries())
        live_entries = sorted((k, v) for k, v in merged.items() if v is not TOMBSTONE)
        self.runs = [SSTable(live_entries, seq=self._next_seq)]
        self._next_seq += 1


def main():
    lsm = LSMTree(flush_threshold=8)
    reference: dict[str, Any] = {}  # ground-truth oracle: plain dict, key absent == deleted

    ops = []
    for i in range(40):
        ops.append(("put", f"k{i:02d}", f"v{i}-a"))
    for i in range(0, 40, 3):
        ops.append(("put", f"k{i:02d}", f"v{i}-b"))  # overwrite: newer value must shadow older
    for i in range(0, 40, 7):
        ops.append(("delete", f"k{i:02d}", None))  # tombstone: must shadow older value entirely
    for i in range(0, 14, 5):
        ops.append(("put", f"k{i:02d}", f"v{i}-resurrected"))  # write after delete: must win

    for op, key, value in ops:
        if op == "put":
            lsm.put(key, value)
            reference[key] = value
        else:
            lsm.delete(key)
            reference.pop(key, None)

    lsm.flush()  # flush whatever's left in the memtable so reads below exercise runs too

    print(f"{len(ops)} ops applied, {lsm.flush_count} SSTables flushed, "
          f"{len(lsm.memtable)} entries still in the active memtable")

    mismatches = []
    for i in range(40):
        key = f"k{i:02d}"
        got = lsm.get(key)
        want = reference.get(key)
        if got != want:
            mismatches.append((key, got, want))
    assert not mismatches, f"read mismatches before compaction: {mismatches}"

    missing_keys_agree = all(lsm.get(f"missing{i}") is None for i in range(5))
    assert missing_keys_agree, "a never-written key returned something other than None"

    print("all reads match the reference model before compaction")

    runs_before = len(lsm.runs)
    lsm.compact()
    runs_after = len(lsm.runs)
    assert runs_after == 1, f"expected compaction to merge down to 1 run, got {runs_after}"

    mismatches_after = []
    for i in range(40):
        key = f"k{i:02d}"
        got = lsm.get(key)
        want = reference.get(key)
        if got != want:
            mismatches_after.append((key, got, want))
    assert not mismatches_after, f"read mismatches after compaction: {mismatches_after}"

    # Deleted keys should have no trace left in storage at all post-compaction (tombstone gone,
    # not just shadowed) - space actually reclaimed, the whole point of compacting.
    surviving_keys = {k for k, _ in lsm.runs[0].entries()}
    deleted_keys = {f"k{i:02d}" for i in range(0, 40, 7)} - reference.keys()
    leaked_tombstones = surviving_keys & deleted_keys
    assert not leaked_tombstones, f"deleted keys still stored after compaction: {leaked_tombstones}"

    print(f"compaction merged {runs_before} runs into {runs_after}, reads still match the reference "
          f"model, and {len(deleted_keys)} deleted keys left no trace")

    print(f"\nself-check passed: {len(ops)} puts/deletes/overwrites across {runs_before} flushed "
          f"SSTables all read back correctly both before and after compaction.")


if __name__ == "__main__":
    main()
