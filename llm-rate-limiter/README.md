# LLM Rate Limiter

## Problem
Design a rate limiter for an LLM API that enforces two independent limits at once: requests per
minute and tokens per minute. A call must be throttled if it would exceed either limit, even if the
other still has room - a single huge-context call should be blockable on tokens alone, and a burst of
tiny calls should be blockable on request count alone.

## Design
- `TokenBucket` - generic bucket of `capacity` units refilling continuously at `refill_rate`
  units/sec; reused for both the request-count bucket and the token-count bucket.
- `LlmRateLimiter` - keeps a pair of `TokenBucket`s per client, one sized in requests/min and one in
  tokens/min. `allow_request(client_id, tokens_requested)` checks *both* buckets have headroom before
  debiting either, so a rejected call never partially consumes a bucket it wasn't allowed to use.
- `FakeClock` - controllable clock injected into every bucket so refill behavior is deterministic.

## Patterns used
- **Strategy**-adjacent reuse - the same `TokenBucket` building block is composed twice with
  different capacities/rates to implement two independently-enforced limits behind one decision.

## How to run
```
cd /Users/bhargav/Desktop/low-level-design/llm-rate-limiter
python3 main.py
```
