"""Rate limiter demo - three strategies behind a common interface (Strategy pattern)."""

from abc import ABC, abstractmethod
from collections import defaultdict, deque


class FakeClock:
    """Controllable clock so the demo is deterministic instead of sleeping real time."""

    def __init__(self):
        self._now = 0.0

    def time(self) -> float:
        return self._now

    def advance(self, seconds: float):
        self._now += seconds


class RateLimiter(ABC):
    @abstractmethod
    def allow_request(self, client_id: str) -> bool:
        """Return True if the request should be let through."""


class TokenBucketLimiter(RateLimiter):
    """Each client gets a bucket of `capacity` tokens that refill at `refill_rate` tokens/sec."""

    def __init__(self, capacity: int, refill_rate: float, clock: FakeClock):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.clock = clock
        self._tokens: dict[str, float] = defaultdict(lambda: float(capacity))
        self._last_refill: dict[str, float] = defaultdict(clock.time)

    def _refill(self, client_id: str):
        now = self.clock.time()
        elapsed = now - self._last_refill[client_id]
        if elapsed > 0:
            self._tokens[client_id] = min(
                self.capacity, self._tokens[client_id] + elapsed * self.refill_rate
            )
            self._last_refill[client_id] = now

    def allow_request(self, client_id: str) -> bool:
        self._refill(client_id)
        if self._tokens[client_id] >= 1:
            self._tokens[client_id] -= 1
            return True
        return False


class FixedWindowCounterLimiter(RateLimiter):
    """Allows up to `max_requests` per fixed-size window; counter resets at window boundaries."""

    def __init__(self, max_requests: int, window_seconds: float, clock: FakeClock):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.clock = clock
        self._window_start: dict[str, float] = {}
        self._count: dict[str, int] = defaultdict(int)

    def allow_request(self, client_id: str) -> bool:
        now = self.clock.time()
        start = self._window_start.get(client_id)
        if start is None or now - start >= self.window_seconds:
            self._window_start[client_id] = now
            self._count[client_id] = 0
        self._count[client_id] += 1
        return self._count[client_id] <= self.max_requests


class SlidingWindowLogLimiter(RateLimiter):
    """Keeps a timestamp log per client and evicts entries older than the window."""

    def __init__(self, max_requests: int, window_seconds: float, clock: FakeClock):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.clock = clock
        self._log: dict[str, deque] = defaultdict(deque)

    def allow_request(self, client_id: str) -> bool:
        now = self.clock.time()
        log = self._log[client_id]
        while log and now - log[0] >= self.window_seconds:
            log.popleft()
        if len(log) < self.max_requests:
            log.append(now)
            return True
        return False


def run_demo(name: str, limiter: RateLimiter, clock: FakeClock, ticks):
    print(f"\n--- {name} ---")
    for i, advance in enumerate(ticks, start=1):
        clock.advance(advance)
        decision = "ALLOW" if limiter.allow_request("client-1") else "DENY"
        print(f"req {i:>2} @ t={clock.time():.1f}s -> {decision}")


def main():
    # 10 quick requests, then a pause, then a few more - shows burst handling and recovery.
    burst_then_pause = [0] * 6 + [0.5] * 2 + [5.0] + [0.1] * 3

    clock1 = FakeClock()
    run_demo(
        "TokenBucketLimiter (capacity=5, refill=1/s)",
        TokenBucketLimiter(capacity=5, refill_rate=1.0, clock=clock1),
        clock1,
        burst_then_pause,
    )

    clock2 = FakeClock()
    run_demo(
        "FixedWindowCounterLimiter (5 req / 3s window)",
        FixedWindowCounterLimiter(max_requests=5, window_seconds=3.0, clock=clock2),
        clock2,
        burst_then_pause,
    )

    clock3 = FakeClock()
    run_demo(
        "SlidingWindowLogLimiter (5 req / 3s window)",
        SlidingWindowLogLimiter(max_requests=5, window_seconds=3.0, clock=clock3),
        clock3,
        burst_then_pause,
    )


if __name__ == "__main__":
    main()
