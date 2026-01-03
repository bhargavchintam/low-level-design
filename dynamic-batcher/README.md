# Dynamic Batcher

## Problem
Design the request-batching policy that sits in front of a model server: group
incoming requests into a batch as soon as either `max_batch_size` is reached
or the oldest pending request has waited `max_wait_s`, whichever comes first.
The batching *decision* needs to be verified exactly - which requests land in
which batch, and why - without depending on real wall-clock timing or thread
scheduling to make the test reproducible.

## Design
- `Clock` (ABC) / `FakeClock` - time only advances when told to
  (`advance_to`), so a test drives the batcher through a scenario at
  full speed with byte-exact, reproducible batch boundaries instead of racing
  a real timer.
- `DynamicBatcher` - FIFO queue of pending requests. `submit()` appends and
  flushes immediately if that push alone crosses a threshold; `poll()` flushes
  whatever is already due with no new arrival needed. `next_deadline()`
  returns the earliest time the batcher must be re-checked even with nothing
  new arriving (oldest pending arrival + `max_wait_s`), or `None` if there's
  nothing pending - a caller only ever needs to wake up then, not on a fixed
  tick.
- `simulate` - drives a fixed arrival schedule by always advancing the clock
  to `min(next arrival, next deadline)`: exactly how an event loop or timer
  wheel schedules wakeups instead of busy-polling.
- Demo scenario: a burst that exactly fills one batch (flushes by size), a
  small trickle that has to wait out the full timeout, then a burst bigger
  than one batch (spills into a second batch, which itself times out since
  nothing else ever arrives). Every batch's reason and membership is asserted
  against hand-computed expected values.

## Patterns used
- **Strategy** (dependency injection) - `Clock` is swappable; `FakeClock`
  makes time a controlled input instead of an environmental side effect,
  which is what makes the exact-batch-boundary assertions possible at all.

## How to run
```
cd /Users/bhargav/Desktop/low-level-design/dynamic-batcher
python3 main.py
```
