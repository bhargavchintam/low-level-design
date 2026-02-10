# Streaming Feature Aggregator

## Problem
Design real-time feature aggregation over an event stream: for a given entity, compute count/sum/avg
over the last N minutes, with the aggregate updating as new events arrive and old events age out of
the window - the kind of feature a model needs at serving time that can't be precomputed offline.

## Design
- `Event` - `entity_id`, `value`, `timestamp`.
- `Aggregation` (ABC) - `compute(values) -> float`; `CountAggregation`, `SumAggregation`,
  `AvgAggregation` are interchangeable reductions over the same window of values.
- `SlidingWindowAggregator` - keeps a per-entity `deque` of `(timestamp, value)` pairs. `add_event`
  appends and evicts anything older than `window_seconds`; `compute` evicts again before reducing, so
  a read is always exact even if no event has arrived recently to trigger eviction on its own.
- `FakeClock` - controllable clock so window boundaries move deterministically in the demo instead of
  depending on wall-clock time.

## Patterns used
- **Strategy** - `Aggregation` implementations are interchangeable reduction algorithms passed into
  `compute`, so adding a new statistic (e.g. max) doesn't touch `SlidingWindowAggregator`.

## How to run
```
cd /Users/bhargav/Desktop/low-level-design/streaming-feature-aggregator
python3 main.py
```
