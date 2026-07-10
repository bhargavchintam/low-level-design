# Consistent Hash Ring

## Problem
Design a key-to-node mapping for a distributed cache/store that doesn't reshuffle almost every key
when a node joins or leaves. Naive `hash(key) % N` remaps nearly all keys the moment `N` changes;
consistent hashing should only move about `1/N` of them, and load across nodes should stay roughly
even even though nodes join at arbitrary times.

## Design
- `HashFunction` (ABC) - `__call__(key) -> int`, the ring's hashing strategy.
- `Md5Hash` - hashes a string to a 128-bit integer via md5; plenty of spread for ring positions.
- `ConsistentHashRing` - `add_node`/`remove_node` place `virtual_nodes` positions per physical node
  onto the ring (each at `hash(f"{node}#{i}")`), kept in a sorted list via `bisect.insort` for
  O(log n) lookups. `get_node(key)` hashes the key and binary-searches for the first ring position
  at or after it (`bisect_right`, wrapping around to index 0 - the ring is circular), returning
  the physical node that owns that position. More virtual nodes per physical node means the ring
  is carved into more, smaller arcs, which is what keeps the *load* distribution even - with only
  one point per node, arc sizes (and thus key counts) would vary wildly by chance.

## Patterns used
- **Strategy** - `HashFunction` is swappable independently of the ring's placement/lookup logic,
  the same separation `vector-store`'s `SimilarityMetric` and `bloom-filter`'s `HashFamily` use.

## How to run
```
cd /Users/bhargav/Desktop/low-level-design/consistent-hash-ring
python3 main.py
```
The demo rings up 5 nodes (200 virtual nodes each) and maps 20,000 keys, checking the pre-add
distribution stays within 30% of the ideal `keys/node`. It then adds a 6th node and asserts: every
key that moved landed on the new node (never reshuffled onto some other pre-existing node), and the
moved fraction (~17%) lands within 5 points of the theoretical `1/6` expectation.
