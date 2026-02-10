"""Streaming feature aggregator - sliding-window count/sum/avg over an event stream, recomputed by
evicting entries older than the window on every read (no periodic sweep, no fixed-bucket rollover)."""

from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass


class FakeClock:
    """Controllable clock so the demo is deterministic instead of sleeping real time."""

    def __init__(self):
        self._now = 0.0

    def time(self) -> float:
        return self._now

    def advance(self, seconds: float):
        self._now += seconds


@dataclass
class Event:
    entity_id: str
    value: float
    timestamp: float


class Aggregation(ABC):
    @abstractmethod
    def compute(self, values: list[float]) -> float:
        ...


class CountAggregation(Aggregation):
    def compute(self, values: list[float]) -> float:
        return len(values)


class SumAggregation(Aggregation):
    def compute(self, values: list[float]) -> float:
        return sum(values)


class AvgAggregation(Aggregation):
    def compute(self, values: list[float]) -> float:
        return sum(values) / len(values) if values else 0.0


class SlidingWindowAggregator:
    """Per-entity deque of (timestamp, value) pairs. Events older than `window_seconds` relative to
    the clock's current time are evicted lazily whenever the window is written to or read, so an
    aggregate always reflects exactly the last `window_seconds` of activity."""

    def __init__(self, window_seconds: float, clock: FakeClock):
        self.window_seconds = window_seconds
        self.clock = clock
        self._events: dict[str, deque] = defaultdict(deque)

    def add_event(self, event: Event):
        self._events[event.entity_id].append((event.timestamp, event.value))
        self._evict_stale(event.entity_id)

    def _evict_stale(self, entity_id: str):
        window = self._events[entity_id]
        cutoff = self.clock.time() - self.window_seconds
        while window and window[0][0] < cutoff:
            window.popleft()

    def compute(self, entity_id: str, aggregation: Aggregation) -> float:
        self._evict_stale(entity_id)
        values = [value for _, value in self._events[entity_id]]
        return aggregation.compute(values)


def main():
    clock = FakeClock()
    window_seconds = 300  # 5-minute sliding window
    aggregator = SlidingWindowAggregator(window_seconds=window_seconds, clock=clock)

    # (seconds since start, transaction amount) - a spend stream for one entity.
    stream = [
        (0, 10), (60, 20), (120, 15), (180, 5), (240, 25),
        (300, 30), (360, 10), (420, 40), (480, 5), (540, 20), (600, 15),
    ]

    print(f"-- sliding {window_seconds}s window over a transaction-amount stream (entity=user-1) --")
    for timestamp, value in stream:
        clock.advance(timestamp - clock.time())
        aggregator.add_event(Event("user-1", value, clock.time()))

        count = aggregator.compute("user-1", CountAggregation())
        total = aggregator.compute("user-1", SumAggregation())
        avg = aggregator.compute("user-1", AvgAggregation())
        print(
            f"t={clock.time() / 60:>4.1f}min  event=+{value:<4} "
            f"-> window[count={count:.0f} sum={total:>5.1f} avg={avg:>5.2f}]"
        )


if __name__ == "__main__":
    main()
