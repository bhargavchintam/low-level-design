# Thread Pool

## Problem
Build a fixed-size worker pool that runs submitted work items on background threads instead of
the caller's own thread. Submitting a task shouldn't block, and the caller needs a way to get the
result (or exception) back later, without polling.

## Design
- `Future` - a handle to a result that doesn't exist yet. Backed by a `threading.Event`;
  `result(timeout=None)` blocks until a worker calls `set_result` or `set_exception`, then returns
  the value or re-raises the exception.
- `_Task` - a callable plus its args/kwargs plus the `Future` it reports to; effectively a Command
  object queued up to run later.
- `ThreadPool` - starts `num_workers` daemon threads on construction, all pulling from one shared
  `queue.Queue`. `submit(fn, *args, **kwargs)` enqueues a `_Task` and returns its `Future`
  immediately. Each worker loop pulls a task, runs it, and routes the outcome (result or exception)
  to that task's `Future` - one `_SHUTDOWN` sentinel per worker unblocks `shutdown()`'s `join()`.

## Patterns used
- **Thread Pool** - a fixed set of reusable worker threads consuming a shared task queue, so the
  number of OS threads stays bounded regardless of how many tasks get submitted.
- **Future/Promise** - `submit()` returns a placeholder for a result that will exist later,
  decoupling "when work is handed off" from "when the result is actually needed" - the same
  contract `concurrent.futures.ThreadPoolExecutor` exposes, built from scratch here.

## How to run
```
cd /Users/bhargav/Desktop/low-level-design/thread-pool
python3 main.py
```
The demo submits 20 `slow_square` tasks (each sleeps 30ms) plus 3 tasks that deliberately divide
by zero, across 4 real worker threads. It asserts every result is correct, every deliberate
exception propagates through its `Future`, more than one worker actually ran a task, and total
wall time is well under the sequential equivalent - proof the pool runs tasks concurrently rather
than one at a time.
