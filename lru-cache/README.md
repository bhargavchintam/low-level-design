# LRU Cache

## Problem
Design a fixed-capacity cache with O(1) `get` and `put`, where inserting a new key past capacity evicts the least recently used entry. Both reading and writing a key count as "using" it and should refresh its recency.

## Design
- `LRUCache<K, V>` — generic cache built from a `HashMap<K, Node<K,V>>` for O(1) lookup plus a hand-rolled doubly linked list for O(1) reordering and eviction. Sentinel `head`/`tail` nodes avoid null-checking the list ends.
- `Node<K, V>` — private static nested class holding a key, value, and `prev`/`next` links.
- `get(key)` moves the node to the front (most recently used) if present.
- `put(key, value)` updates-and-moves an existing key, or inserts a new node at the front, evicting the tail's neighbor (least recently used) first if the cache is at capacity.

## Patterns used
- No single GoF pattern is the point here — this is a from-scratch data structure exercise (HashMap + doubly linked list) rather than a design-pattern problem, so none is forced in.

## How to run
```
cd lru-cache
java Main.java
```
