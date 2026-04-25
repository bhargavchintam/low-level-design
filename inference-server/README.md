# Inference Server

## Problem
Design a serving layer that sits in front of a model and batches concurrent
requests together instead of running each one through the model individually
(dynamic batching - the standard trick for making GPU inference throughput-efficient).
Requests arrive from independent callers at unpredictable times; the server must
group whatever arrived within a small window into one forward pass, without
making any individual caller wait past a bounded latency budget.

## Design
- `ModelHandler` (ABC) - `predict_batch(payloads) -> results`, one forward pass
  over a whole batch. `SquareModel` is a stand-in with a fixed per-batch
  overhead plus a small per-item cost, so batching genuinely amortizes.
- `_PendingRequest` - one caller's request: payload, arrival timestamp, a
  `threading.Event` the caller blocks on, and the result slot the batcher
  fills in once its batch has been computed.
- `DynamicBatcher` - owns a `queue.Queue` inbox and a single worker thread.
  The worker pulls the first request, then keeps pulling more (with a
  shrinking timeout) until either `max_batch_size` is reached or
  `max_wait_s` elapses since the first request arrived - whichever comes
  first - then runs one `predict_batch` call and wakes every caller in that
  batch via its `Event`.
- `simulate_client` - real threads submit requests with bursty (clumped)
  arrival times, which is the traffic shape that makes dynamic batching pay
  off; steady one-at-a-time traffic wouldn't batch regardless of window size.

## Patterns used
- **Strategy** - `ModelHandler` is the swappable compute strategy; the batcher
  has no idea whether it's calling a toy function or a real model.
- Producer/consumer via `queue.Queue` - many client threads produce, one
  batcher thread consumes and flushes, decoupling arrival timing from
  compute timing.

## How to run
```
cd /Users/bhargav/Desktop/low-level-design/inference-server
python3 main.py
```
