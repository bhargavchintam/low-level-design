# Circuit Breaker

## Problem
Design a circuit breaker that protects callers from a flaky downstream service: stop hammering a
service that's failing (open), periodically test whether it has recovered (half-open), and resume
normal traffic once it has (closed) - without every caller having to reimplement this logic.

## Design
- `CircuitState` (ABC) - `allow_request(breaker)`, `on_success(breaker)`, `on_failure(breaker)`, plus
  an optional `on_enter(breaker)` hook run on transition into the state.
- `ClosedState` - calls pass through; `failure_threshold` consecutive failures trips to `OpenState`.
- `OpenState` - rejects every call immediately (the underlying service is never called) until
  `recovery_timeout` has elapsed since it opened, then transitions to `HalfOpenState` and retries
  the check.
- `HalfOpenState` - allows exactly one trial call; success closes the circuit, failure reopens it.
- `CircuitBreaker` - holds the current `CircuitState` and delegates `call(func)` to it, tracking
  `consecutive_failures` and driving `transition_to`.
- `FakeClock` - controllable clock so the open -> half-open timeout is deterministic in the demo.

## Patterns used
- **State** - `CircuitBreaker` delegates all call-admission and transition logic to its current
  `CircuitState` object; behavior changes completely based on which state is active, without any
  conditionals in `CircuitBreaker` itself.

## How to run
```
cd /Users/bhargav/Desktop/low-level-design/circuit-breaker
python3 main.py
```
