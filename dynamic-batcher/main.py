"""Dynamic batcher - groups requests into batches by size-or-timeout, driven entirely
through an injected Clock so the exact batch boundaries are deterministic and testable
without a real thread, a real sleep, or a millisecond of wall-clock time.

Rather than busy-polling on a fixed interval, the batcher exposes next_deadline():
the next timestamp at which its pending state must be re-examined for a timeout. A
driver only ever needs to advance the clock to min(next arrival, next deadline) -
exactly how a real event loop / timer wheel schedules wakeups instead of spinning.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


class Clock(ABC):
    @abstractmethod
    def now(self) -> float:
        ...


class FakeClock(Clock):
    """Time only moves when the test tells it to - the whole point being that batch
    boundaries in the demo are exact and reproducible, not racy against a scheduler."""

    def __init__(self, start: float = 0.0):
        self._t = start

    def now(self) -> float:
        return self._t

    def advance_to(self, t: float):
        assert t >= self._t, "clock cannot move backwards"
        self._t = t


@dataclass
class Request:
    id: int
    payload: str
    arrival_ts: float


@dataclass
class Batch:
    requests: list[Request]
    formed_ts: float
    reason: str  # "size" or "timeout"

    @property
    def ids(self) -> list[int]:
        return [r.id for r in self.requests]


class DynamicBatcher:
    """Buffers submitted requests FIFO. A flush fires the moment either threshold is
    crossed: `max_batch_size` requests are pending, or the oldest pending request has
    been waiting `max_wait_s`. submit() and poll() both drain as many batches as are
    immediately due (a single clock jump can make more than one threshold true at
    once if, e.g., a huge burst arrives well past a prior deadline)."""

    def __init__(self, clock: Clock, max_batch_size: int, max_wait_s: float):
        self.clock = clock
        self.max_batch_size = max_batch_size
        self.max_wait_s = max_wait_s
        self._pending: list[Request] = []
        self.batches: list[Batch] = []

    def has_pending(self) -> bool:
        return bool(self._pending)

    def next_deadline(self) -> float | None:
        """Earliest time the batcher needs to be re-examined even with no new
        arrivals - None means it's fine to sleep until the next arrival."""
        if not self._pending:
            return None
        return self._pending[0].arrival_ts + self.max_wait_s

    def submit(self, request: Request) -> list[Batch]:
        self._pending.append(request)
        return self.poll()

    def poll(self) -> list[Batch]:
        formed = []
        while True:
            reason = self._flush_reason()
            if reason is None:
                break
            formed.append(self._flush(reason))
        return formed

    def _flush_reason(self) -> str | None:
        if not self._pending:
            return None
        if len(self._pending) >= self.max_batch_size:
            return "size"
        # Epsilon guard: next_deadline() and this check both compute arrival_ts +
        # max_wait_s from the same numbers but not always the same associativity,
        # so a strict >= can flap false right at the boundary and spin forever.
        if self.clock.now() - self._pending[0].arrival_ts >= self.max_wait_s - 1e-9:
            return "timeout"
        return None

    def _flush(self, reason: str) -> Batch:
        batch_reqs, self._pending = self._pending[: self.max_batch_size], self._pending[self.max_batch_size:]
        batch = Batch(batch_reqs, self.clock.now(), reason)
        self.batches.append(batch)
        return batch


def simulate(batcher: DynamicBatcher, clock: FakeClock, arrivals: list[tuple[float, int, str]]) -> list[Batch]:
    """Drives the batcher through a fixed arrival schedule [(time, id, payload), ...],
    sorted by time. Advances the fake clock only to points that matter (next arrival
    or next timeout deadline) - never a fixed tick - then submits whatever arrives
    exactly at that instant and polls for any timeout that just came due."""
    arrivals = sorted(arrivals, key=lambda a: a[0])
    i = 0
    formed: list[Batch] = []

    while i < len(arrivals) or batcher.has_pending():
        next_arrival_t = arrivals[i][0] if i < len(arrivals) else None
        deadline = batcher.next_deadline()
        candidates = [t for t in (next_arrival_t, deadline) if t is not None]
        clock.advance_to(min(candidates))

        while i < len(arrivals) and arrivals[i][0] == clock.now():
            t, rid, payload = arrivals[i]
            formed += batcher.submit(Request(rid, payload, t))
            i += 1

        formed += batcher.poll()  # catches a timeout deadline reached with no new arrival

    return formed


def main():
    clock = FakeClock()
    batcher = DynamicBatcher(clock, max_batch_size=4, max_wait_s=0.5)

    # A burst that fills a batch exactly, a small trickle that has to wait out the
    # timeout, then another burst bigger than one batch (spills into a second, which
    # itself has to wait out the timeout since nothing else arrives after it).
    arrivals = (
        [(0.00, i, f"req-{i}") for i in range(0, 4)]
        + [(0.10, i, f"req-{i}") for i in range(4, 6)]
        + [(0.65, i, f"req-{i}") for i in range(6, 11)]
    )

    formed = simulate(batcher, clock, arrivals)

    print(f"{'batch':>5} {'reason':>8} {'formed_ts':>10}   ids")
    for i, b in enumerate(formed):
        print(f"{i:>5} {b.reason:>8} {b.formed_ts:>10.2f}   {b.ids}")

    total_requests = len(arrivals)
    total_batched = sum(len(b.requests) for b in formed)
    reasons = [b.reason for b in formed]
    all_ids = [rid for b in formed for rid in b.ids]

    print(f"\n{total_requests} requests submitted -> {len(formed)} batches, "
          f"{total_batched} requests accounted for")

    assert total_batched == total_requests, "every submitted request must end up in exactly one batch"
    assert all_ids == list(range(total_requests)), "FIFO order must be preserved across batches"
    assert all(len(b.requests) <= batcher.max_batch_size for b in formed), "no batch may exceed max_batch_size"
    assert reasons == ["size", "timeout", "size", "timeout"], f"unexpected flush reasons: {reasons}"

    # The two timeout batches must each have waited AT LEAST max_wait_s, and no batch
    # (size or timeout) may have waited less than zero or been flushed early.
    for b in formed:
        oldest_wait = b.formed_ts - b.requests[0].arrival_ts
        assert oldest_wait >= -1e-9
        if b.reason == "timeout":
            assert oldest_wait >= batcher.max_wait_s - 1e-9, f"batch flushed before its timeout: waited {oldest_wait}"

    print("\nself-check passed: every request landed in exactly one batch, FIFO order held, "
          "size batches never exceeded capacity, and timeout batches never flushed early.")


if __name__ == "__main__":
    main()
