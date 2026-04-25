"""Inference server demo - request queue with dynamic batching in front of a model handler.

Real threads simulate concurrent clients; a single batcher thread groups whatever
arrived within a small window into one forward pass, trading a little latency for
throughput (the standard serving trick: batch(4) is cheaper per-item than 4x batch(1)).
"""

import queue
import random
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


class ModelHandler(ABC):
    """Strategy the batcher delegates compute to - swap in a real model without touching batching logic."""

    @abstractmethod
    def predict_batch(self, payloads: list[int]) -> list[int]:
        """Run one forward pass over the whole batch, return one result per input."""


class SquareModel(ModelHandler):
    """Stand-in for a real model: fixed per-batch overhead plus a small per-item cost."""

    def __init__(self, fixed_cost_s: float = 0.05, per_item_cost_s: float = 0.01):
        self.fixed_cost_s = fixed_cost_s
        self.per_item_cost_s = per_item_cost_s

    def predict_batch(self, payloads: list[int]) -> list[int]:
        time.sleep(self.fixed_cost_s + self.per_item_cost_s * len(payloads))
        return [x * x for x in payloads]


@dataclass
class _PendingRequest:
    request_id: int
    payload: int
    arrival_ts: float
    done: threading.Event = field(default_factory=threading.Event)
    result: int | None = None
    latency_s: float = 0.0


@dataclass
class BatchStats:
    batch_id: int
    size: int
    wait_s: float
    compute_s: float


class DynamicBatcher:
    """Collects incoming requests and flushes a batch when it's full or max_wait_s elapses,
    whichever comes first. Runs its own worker thread so submit() can block the caller
    without blocking other callers."""

    def __init__(self, model: ModelHandler, max_batch_size: int = 8, max_wait_s: float = 0.08):
        self.model = model
        self.max_batch_size = max_batch_size
        self.max_wait_s = max_wait_s
        self._inbox: queue.Queue[_PendingRequest | None] = queue.Queue()
        self._next_id = 0
        self._next_batch_id = 0
        self._id_lock = threading.Lock()
        self.batch_log: list[BatchStats] = []
        self._worker = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._worker.start()

    def stop(self):
        self._inbox.put(None)  # sentinel unblocks a pending get()
        self._worker.join()

    def submit(self, payload: int) -> tuple[int, float]:
        """Blocks until this request's slot in some batch has been computed."""
        with self._id_lock:
            req = _PendingRequest(self._next_id, payload, time.monotonic())
            self._next_id += 1
        self._inbox.put(req)
        req.done.wait()
        return req.result, req.latency_s

    def _run(self):
        while True:
            first = self._inbox.get()
            if first is None:
                return

            batch = [first]
            deadline = time.monotonic() + self.max_wait_s
            while len(batch) < self.max_batch_size:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                try:
                    item = self._inbox.get(timeout=remaining)
                except queue.Empty:
                    break
                if item is None:  # shutdown while a batch was still forming
                    self._flush(batch)
                    return
                batch.append(item)

            self._flush(batch)

    def _flush(self, batch: list[_PendingRequest]):
        wait_s = time.monotonic() - batch[0].arrival_ts
        t0 = time.monotonic()
        results = self.model.predict_batch([r.payload for r in batch])
        compute_s = time.monotonic() - t0

        self.batch_log.append(BatchStats(self._next_batch_id, len(batch), wait_s, compute_s))
        self._next_batch_id += 1

        for req, result in zip(batch, results):
            req.result = result
            req.latency_s = time.monotonic() - req.arrival_ts
            req.done.set()


def simulate_client(batcher: DynamicBatcher, payload: int, delay_s: float, out: list):
    time.sleep(delay_s)
    result, latency = batcher.submit(payload)
    out.append((payload, result, latency))


def main():
    model = SquareModel(fixed_cost_s=0.05, per_item_cost_s=0.01)
    batcher = DynamicBatcher(model, max_batch_size=8, max_wait_s=0.08)
    batcher.start()

    rng = random.Random(7)
    n_requests = 24
    results: list[tuple[int, int, float]] = []
    threads = []
    for i in range(n_requests):
        # Bursty arrivals: clumps of near-simultaneous requests separated by gaps,
        # which is what makes dynamic batching worth it (steady one-at-a-time traffic
        # wouldn't batch no matter the window).
        delay = (i // 6) * 0.15 + rng.uniform(0, 0.02)
        t = threading.Thread(target=simulate_client, args=(batcher, i, delay, results))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()
    batcher.stop()

    results.sort(key=lambda r: r[0])
    print(f"{'payload':>7} {'result':>7} {'latency_ms':>11}")
    for payload, result, latency in results:
        print(f"{payload:>7} {result:>7} {latency * 1000:>10.1f}")

    print(f"\n{len(batcher.batch_log)} batches formed for {n_requests} requests:")
    for b in batcher.batch_log:
        print(f"  batch {b.batch_id}: size={b.size:>2}  wait={b.wait_s*1000:5.1f}ms  compute={b.compute_s*1000:5.1f}ms")

    avg_batch_size = n_requests / len(batcher.batch_log)
    assert sum(b.size for b in batcher.batch_log) == n_requests
    assert avg_batch_size > 1.0, "batching had no effect - traffic wasn't bursty enough"
    print(f"\nself-check passed: {n_requests} requests -> {len(batcher.batch_log)} batches "
          f"(avg batch size {avg_batch_size:.1f}, so batching is actually happening).")


if __name__ == "__main__":
    main()
