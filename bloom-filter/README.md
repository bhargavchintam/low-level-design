# Bloom Filter

## Problem
Design a compact, probabilistic set for membership testing where an exact hash set would use too
much memory. False positives are acceptable within a target rate; false negatives are never
acceptable - if the filter says "definitely not present," that has to be true 100% of the time.

## Design
- `HashFamily` (ABC) - `positions(item, m, k) -> k bit positions in [0, m)`.
- `DoubleHashingFamily` - Kirsch-Mitzenmacher double hashing: derives all `k` positions from just
  two real hash halves (`h1`, `h2` split out of one sha256 digest) via `h1 + i*h2 (mod m)`, instead
  of computing `k` genuinely independent hash functions. This is what real Bloom filter libraries
  (e.g. Guava) do in practice - it's statistically as good as independent hashes.
- `BloomFilter` - sized at construction from `capacity` and a target `false_positive_rate` using
  the standard closed-form formulas for bit-array size `m` and hash count `k`. Backed by a numpy
  boolean array. `add(item)` sets its `k` bit positions; `item in filter` checks all `k` are set.
  `estimated_false_positive_rate()` recomputes the textbook `(1 - e^(-kn/m))^k` estimate from the
  actual insert count.

## Patterns used
- **Strategy** - `HashFamily` is the swappable "how do we turn one item into k bit positions"
  algorithm; `BloomFilter` only depends on the interface, not the hashing technique.

## How to run
```
cd /Users/bhargav/Desktop/low-level-design/bloom-filter
python3 main.py
```
The demo sizes a filter for 5,000 items at a 1% target false-positive rate, inserts all 5,000, and
asserts zero false negatives (every inserted item tests positive). It then probes 200,000 keys that
were never inserted and asserts the measured false-positive rate lands close to both the 1% design
target and the theoretical estimate computed from the actual bit-array load (typically ~1.0-1.1%).
