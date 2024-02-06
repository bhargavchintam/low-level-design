# Rate Limiter

## Problem
Design a rate limiter that decides whether a client's request should be allowed or rejected, based on a configurable policy. It should support multiple limiting algorithms that can be swapped without changing the code that calls the limiter, and each algorithm must track state per client.

## Design
- `RateLimiter` (ABC) - defines `allow_request(client_id) -> bool`, the single contract every strategy implements.
- `TokenBucketLimiter` - per-client bucket of tokens that refills continuously at a fixed rate; a request consumes one token if available.
- `FixedWindowCounterLimiter` - per-client counter that resets whenever the current fixed-size time window has elapsed.
- `SlidingWindowLogLimiter` - per-client deque of request timestamps; old timestamps outside the window are evicted before checking the limit.
- `FakeClock` - a controllable clock injected into every limiter so the demo is deterministic (no real sleeping, no flakiness).

## Patterns used
- **Strategy** - `RateLimiter` is the strategy interface; `TokenBucketLimiter`, `FixedWindowCounterLimiter`, and `SlidingWindowLogLimiter` are interchangeable algorithms the caller picks at construction time without changing how `allow_request` is called.

## How to run
```
cd /Users/bhargav/Desktop/low-level-design/rate-limiter
python3 main.py
```
