# AB Test Assignment

## Problem
Design experiment bucketing that assigns each user to a variant such that the same user always gets
the same variant on every call, the split across variants roughly matches configured weights, and no
per-user assignment table needs to be stored or looked up. A user's bucket in one experiment also
shouldn't be correlated with their bucket in another.

## Design
- `HashStrategy` (ABC) - `to_unit_interval(key) -> float`, mapping an arbitrary string into `[0, 1)`.
- `Md5HashStrategy` - stable hash-based implementation.
- `Variant` - a name and a traffic weight.
- `Experiment` - holds a list of `Variant`s (weights must sum to 1.0) and precomputed cumulative
  weight boundaries. `assign(user_id)` hashes `"{experiment_name}:{user_id}"`, so the experiment name
  acts as a salt that decorrelates the same user's bucket across different experiments, then locates
  which boundary the hashed point falls under via binary search.

## Patterns used
- **Strategy** - `HashStrategy` is swappable independently of `Experiment`, so the hashing algorithm
  can change without touching the bucketing logic.

## How to run
```
cd /Users/bhargav/Desktop/low-level-design/ab-test-assignment
python3 main.py
```
