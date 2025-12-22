# Priority Scheduler

## Problem
Design a job scheduler where lower-priority work can't starve forever behind
a continuous stream of higher-priority arrivals. A plain priority heap alone
doesn't solve this - a job submitted with low priority loses every comparison
against any later, more urgent arrival, indefinitely. Priority *aging*
(gradually boosting a waiting job's priority the longer it sits) is what
bounds the worst case.

## Design
- `Job` - id, `base_priority`, `submit_tick`, current (mutable) `priority`,
  `last_boost_tick`, and a `version` counter used to invalidate stale heap
  entries.
- `PriorityScheduler` - a min-heap of `(priority, seq, version, job_id)`
  tuples; lower priority number runs first, the monotonic `seq` counter
  breaks ties FIFO. `heapq` has no decrease-key operation, so `age(now)`
  promotes a waiting job by pushing a *new* heap entry with a bumped
  `version` rather than mutating the old one in place - the standard
  lazy-deletion trick. `run_next` pops until it finds an entry whose
  `version` still matches the job's current version; anything older is a
  stale duplicate left behind by an earlier promotion and is silently
  discarded.
- `run_simulation` - the starvation setup: one low-priority job `L`
  submitted at tick 0, then a fresh highest-priority job every following
  tick, with exactly one job processed per tick. Run twice with identical
  arrivals - once with aging enabled, once disabled - so the contrast in
  outcomes is the proof, not just L's final state in isolation.

## Patterns used
- Lazy deletion for a priority queue without decrease-key - `version`
  stamping turns "update a job's priority" into "push a fresh entry, let old
  ones rot," which is the standard way to fake decrease-key on top of
  `heapq`.
- The aging pass is a small **Strategy**-shaped hook (`age`) the scheduler
  calls once per tick; swapping in a different aging curve (e.g. faster
  promotion for a "starvation-critical" job class) only touches that method.

## How to run
```
cd /Users/bhargav/Desktop/low-level-design/priority-scheduler
python3 main.py
```
