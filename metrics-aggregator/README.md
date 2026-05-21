# Metrics Aggregator

## Problem
Build a streaming metrics aggregator for something like request latency: cheap running counters
(count, sum, min, max, mean, stddev) computed online without storing every observation, plus
quantile estimates (p50, p99) that a fixed-size aggregate normally can't give you exactly - but
should be able to approximate closely without unbounded memory growth as the stream gets long.

## Design
- `RunningStats` - count/sum/min/max updated exactly in O(1); mean/variance via **Welford's online
  algorithm** (`mean` and `M2`, the running sum of squared deviations, both updated per
  observation) - numerically stable in a way naively accumulating `sum(x)` and `sum(x**2)` isn't.
- `QuantileSketch` (ABC) - `observe(value)`, `quantile(q) -> interpolated estimate`.
  - `ExactQuantileSketch` - keeps every value sorted via `bisect.insort`. O(n) memory; the ground
    truth other sketches are checked against.
  - `ReservoirQuantileSketch` - **Algorithm R** reservoir sampling: maintains a uniform random
    sample of fixed size `capacity` out of an arbitrarily long stream (each new item replaces a
    uniformly random existing one with probability `capacity / n_seen`). O(capacity) memory
    regardless of stream length; quantiles are estimated from the sample.
- `MetricsAggregator` - facade holding one `RunningStats` + one `QuantileSketch` per metric name
  behind `record(metric, value)` / `summary(metric) -> MetricSummary`.

## Patterns used
- **Strategy** - `QuantileSketch` implementations (exact vs. bounded-memory-approximate) are
  interchangeable, the same exact-vs-approximate trade `vector-store`'s `BruteForceIndex` /
  `IVFIndex` pair makes.
- **Facade** - `MetricsAggregator` hides the per-metric counter + sketch bookkeeping behind two
  methods.

## How to run
```
cd /Users/bhargav/Desktop/low-level-design/metrics-aggregator
python3 main.py
```
The demo streams 50,000 lognormal-distributed latencies (realistic long-tailed shape) through a
`ReservoirQuantileSketch` of capacity 2,000 (4% of the stream). It asserts count/mean/min/max match
numpy's exact values bit-for-bit, `ExactQuantileSketch` matches `np.percentile` exactly, and the
reservoir's p50/p99 estimates land within a few percent of the true values computed from the full
50,000-point stream (typically ~3% error on both).
