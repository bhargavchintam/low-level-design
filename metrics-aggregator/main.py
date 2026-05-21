"""Streaming metrics aggregator - counters (count/sum/min/max/mean/stddev) computed online in O(1)
per observation via Welford's algorithm, plus a quantile sketch for p50/p99 that never stores the
full stream. QuantileSketch has two implementations: ExactQuantileSketch keeps every value (the
ground truth, O(n) memory) and ReservoirQuantileSketch keeps a fixed-size uniform random sample
(Algorithm R, O(capacity) memory regardless of stream length) - the same bounded-memory-for-a-bit-
of-error trade `vector-store`'s IVFIndex makes against brute force."""

import bisect
import random
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass

import numpy as np


class RunningStats:
    """count/sum/min/max exactly, plus mean/variance via Welford's online algorithm - each
    observation updates the running mean and M2 (sum of squared deviations) in O(1) with no
    numerical blowup from summing squares directly."""

    def __init__(self):
        self.count = 0
        self.sum = 0.0
        self.min = float("inf")
        self.max = float("-inf")
        self._mean = 0.0
        self._m2 = 0.0

    def observe(self, value: float):
        self.count += 1
        self.sum += value
        self.min = min(self.min, value)
        self.max = max(self.max, value)
        delta = value - self._mean
        self._mean += delta / self.count
        self._m2 += delta * (value - self._mean)

    @property
    def mean(self) -> float:
        return self._mean if self.count else 0.0

    @property
    def variance(self) -> float:
        return self._m2 / self.count if self.count else 0.0

    @property
    def stddev(self) -> float:
        return self.variance ** 0.5


class QuantileSketch(ABC):
    @abstractmethod
    def observe(self, value: float):
        ...

    @abstractmethod
    def quantile(self, q: float) -> float:
        """Linear-interpolated estimate of the q-th quantile, q in [0, 1]."""


class ExactQuantileSketch(QuantileSketch):
    """Ground truth: keeps every value ever seen, sorted via bisect.insort. O(n) memory - fine
    for small streams or as the answer ReservoirQuantileSketch is checked against."""

    def __init__(self):
        self._sorted: list[float] = []

    def observe(self, value: float):
        bisect.insort(self._sorted, value)

    def quantile(self, q: float) -> float:
        return _interpolated_quantile(self._sorted, q)


class ReservoirQuantileSketch(QuantileSketch):
    """Algorithm R reservoir sampling: maintains a uniform random sample of fixed size `capacity`
    out of an arbitrarily long stream, each new item replacing a uniformly random existing one with
    probability capacity/n_seen. Bounded memory regardless of stream length; quantiles are
    estimated from the sample instead of the full stream."""

    def __init__(self, capacity: int, seed: int = 0):
        self.capacity = capacity
        self._rng = random.Random(seed)
        self._reservoir: list[float] = []
        self._n_seen = 0

    def observe(self, value: float):
        self._n_seen += 1
        if len(self._reservoir) < self.capacity:
            self._reservoir.append(value)
        else:
            j = self._rng.randint(0, self._n_seen - 1)  # 0-indexed Algorithm R
            if j < self.capacity:
                self._reservoir[j] = value

    def quantile(self, q: float) -> float:
        return _interpolated_quantile(sorted(self._reservoir), q)


def _interpolated_quantile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        return 0.0
    pos = q * (len(sorted_values) - 1)
    lo, hi = int(pos), min(int(pos) + 1, len(sorted_values) - 1)
    frac = pos - lo
    return sorted_values[lo] * (1 - frac) + sorted_values[hi] * frac


@dataclass
class MetricSummary:
    count: int
    sum: float
    mean: float
    stddev: float
    min: float
    max: float
    p50: float
    p99: float


class MetricsAggregator:
    """Facade: one RunningStats + one QuantileSketch per metric name, hidden behind record/summary
    so callers never touch either directly."""

    def __init__(self, sketch_factory=lambda: ReservoirQuantileSketch(capacity=1000)):
        self._sketch_factory = sketch_factory
        self._stats: dict[str, RunningStats] = defaultdict(RunningStats)
        self._sketches: dict[str, QuantileSketch] = {}

    def record(self, metric: str, value: float):
        self._stats[metric].observe(value)
        if metric not in self._sketches:
            self._sketches[metric] = self._sketch_factory()
        self._sketches[metric].observe(value)

    def summary(self, metric: str) -> MetricSummary:
        s = self._stats[metric]
        sketch = self._sketches[metric]
        return MetricSummary(s.count, s.sum, s.mean, s.stddev, s.min, s.max,
                              sketch.quantile(0.50), sketch.quantile(0.99))


def main():
    rng = np.random.default_rng(7)
    n = 50_000
    # Lognormal: the classic shape for request latencies - mostly small, a long right tail.
    latencies_ms = rng.lognormal(mean=3.0, sigma=0.8, size=n)

    aggregator = MetricsAggregator(sketch_factory=lambda: ReservoirQuantileSketch(capacity=2000, seed=1))
    for v in latencies_ms:
        aggregator.record("request_latency_ms", float(v))

    summary = aggregator.summary("request_latency_ms")

    true_mean, true_min, true_max = latencies_ms.mean(), latencies_ms.min(), latencies_ms.max()
    true_p50, true_p99 = np.percentile(latencies_ms, 50), np.percentile(latencies_ms, 99)

    print(f"{n} observations of request_latency_ms\n")
    print(f"{'stat':<10}{'aggregator':>14}{'true (exact)':>16}")
    print(f"{'count':<10}{summary.count:>14}{n:>16}")
    print(f"{'mean':<10}{summary.mean:>14.3f}{true_mean:>16.3f}")
    print(f"{'min':<10}{summary.min:>14.3f}{true_min:>16.3f}")
    print(f"{'max':<10}{summary.max:>14.3f}{true_max:>16.3f}")
    print(f"{'p50':<10}{summary.p50:>14.3f}{true_p50:>16.3f}")
    print(f"{'p99':<10}{summary.p99:>14.3f}{true_p99:>16.3f}")

    # count/sum/min/max/mean are exact by construction (no sampling involved) - must match exactly.
    assert summary.count == n
    assert abs(summary.mean - true_mean) < 1e-6
    assert summary.min == true_min
    assert summary.max == true_max

    # Quantiles came from a 2000-item reservoir sampled out of 50,000 - approximate by design, but
    # should land close to the true value computed from the full stream.
    p50_err = abs(summary.p50 - true_p50) / true_p50
    p99_err = abs(summary.p99 - true_p99) / true_p99
    print(f"\np50 relative error: {p50_err:.2%}   p99 relative error: {p99_err:.2%}")
    assert p50_err < 0.10, f"p50 estimate too far off ({p50_err:.2%})"
    assert p99_err < 0.20, f"p99 estimate too far off ({p99_err:.2%})"  # tail is sparser in the sample

    # Cross-check the reservoir against ExactQuantileSketch fed the identical stream.
    exact = ExactQuantileSketch()
    for v in latencies_ms:
        exact.observe(float(v))
    assert abs(exact.quantile(0.50) - true_p50) < 1e-9
    assert abs(exact.quantile(0.99) - true_p99) < 1e-9

    print(f"\nself-check passed: exact counters match numpy ground truth exactly, "
          f"ExactQuantileSketch matches np.percentile exactly, and the 2000-sample "
          f"ReservoirQuantileSketch estimates p50/p99 within {p50_err:.1%}/{p99_err:.1%} "
          f"of true values while storing 4% of the stream.")


if __name__ == "__main__":
    main()
