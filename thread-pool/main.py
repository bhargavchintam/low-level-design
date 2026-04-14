"""Thread pool - a fixed number of worker threads pull Task objects off a shared queue and run
them; submit() hands back a Future immediately instead of blocking, so the caller decides when
(and whether) to wait for the result. Real threads, real timing - the point is to show actual
concurrency, not simulate it."""

import queue
import random
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable


class Future:
    """A handle to a result that may not exist yet. Exactly one of set_result/set_exception is
    called by whichever worker runs the task; result() blocks until that happens."""

    def __init__(self):
        self._event = threading.Event()
        self._result: Any = None
        self._exception: BaseException | None = None
        self.worker_name: str = ""

    def set_result(self, value: Any):
        self._result = value
        self._event.set()

    def set_exception(self, exc: BaseException):
        self._exception = exc
        self._event.set()

    def done(self) -> bool:
        return self._event.is_set()

    def result(self, timeout: float | None = None) -> Any:
        if not self._event.wait(timeout):
            raise TimeoutError("future not done in time")
        if self._exception is not None:
            raise self._exception
        return self._result


@dataclass
class _Task:
    fn: Callable
    args: tuple
    kwargs: dict
    future: Future


_SHUTDOWN = object()  # sentinel: one per worker, unblocks its queue.get() and ends its loop


class ThreadPool:
    """Owns `num_workers` daemon threads sharing one queue.Queue. submit() wraps a callable as a
    Task with a fresh Future, enqueues it, and returns the Future without waiting - decoupling
    "when work is submitted" from "when its result is needed", the same contract as
    concurrent.futures.ThreadPoolExecutor but hand-rolled to show what's underneath it."""

    def __init__(self, num_workers: int):
        self.num_workers = num_workers
        self._queue: queue.Queue = queue.Queue()
        self._workers = [
            threading.Thread(target=self._worker_loop, name=f"worker-{i}", daemon=True)
            for i in range(num_workers)
        ]
        self.tasks_completed = 0
        self._completed_lock = threading.Lock()
        for w in self._workers:
            w.start()

    def submit(self, fn: Callable, *args, **kwargs) -> Future:
        future = Future()
        self._queue.put(_Task(fn, args, kwargs, future))
        return future

    def _worker_loop(self):
        while True:
            task = self._queue.get()
            if task is _SHUTDOWN:
                self._queue.task_done()
                return
            task.future.worker_name = threading.current_thread().name
            try:
                result = task.fn(*task.args, **task.kwargs)
            except Exception as e:
                task.future.set_exception(e)
            else:
                task.future.set_result(result)
            finally:
                with self._completed_lock:
                    self.tasks_completed += 1
                self._queue.task_done()

    def shutdown(self, wait: bool = True):
        for _ in self._workers:
            self._queue.put(_SHUTDOWN)
        if wait:
            for w in self._workers:
                w.join()


def slow_square(x: int, delay_s: float) -> int:
    time.sleep(delay_s)
    return x * x


def flaky_divide(a: int, b: int) -> float:
    return a / b  # deliberately raises ZeroDivisionError for b == 0, to exercise Future.result()


def main():
    num_workers = 4
    pool = ThreadPool(num_workers)

    rng = random.Random(3)
    n_tasks = 20
    delay_s = 0.03
    futures: list[tuple[int, Future]] = []
    for i in range(n_tasks):
        futures.append((i, pool.submit(slow_square, i, delay_s)))

    # A few tasks deliberately raise, to prove exceptions travel through the Future intact.
    error_futures = [pool.submit(flaky_divide, 10, 0) for _ in range(3)]

    t0 = time.monotonic()
    results = [(i, f.result(), f.worker_name) for i, f in futures]
    wall_s = time.monotonic() - t0

    print(f"{'input':>6} {'result':>7}  worker")
    for i, r, worker in results:
        print(f"{i:>6} {r:>7}  {worker}")
        assert r == i * i, f"wrong result for input {i}: got {r}"

    workers_used = {worker for _, _, worker in results}

    for f in error_futures:
        try:
            f.result()
            raise AssertionError("expected ZeroDivisionError to propagate through Future")
        except ZeroDivisionError:
            pass

    sequential_s = n_tasks * delay_s
    print(f"\n{n_tasks} tasks x {delay_s * 1000:.0f}ms each, {num_workers} workers, "
          f"{len(workers_used)} distinct workers actually used")
    print(f"sequential would take ~{sequential_s * 1000:.0f}ms, pool took {wall_s * 1000:.0f}ms")

    pool.shutdown(wait=True)

    total_submitted = n_tasks + len(error_futures)
    assert pool.tasks_completed == total_submitted, (
        f"expected {total_submitted} completions, got {pool.tasks_completed}"
    )
    assert len(workers_used) > 1, "only one worker ever ran a task - not exercising concurrency"
    assert wall_s < sequential_s * 0.8, (
        f"pool wasn't faster than sequential ({wall_s:.3f}s vs {sequential_s:.3f}s) - "
        "workers aren't actually running concurrently"
    )
    print(
        f"\nself-check passed: all {total_submitted} tasks completed with correct results/exceptions, "
        f"{len(workers_used)} workers shared the load, and wall time ({wall_s * 1000:.0f}ms) beats "
        f"sequential ({sequential_s * 1000:.0f}ms), confirming real concurrency."
    )


if __name__ == "__main__":
    main()
