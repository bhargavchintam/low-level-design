# Model Router

## Problem
Design a router that sends inference requests to one of several model versions: a canary rollout
that sends a small percentage of traffic to a new version, a general weighted A/B split across
versions, and a fallback to another backend when the chosen one errors instead of surfacing the
failure to the caller.

## Design
- `ModelBackend` (ABC) - `predict(request_id) -> str`.
- `SimpleModelBackend` - deterministically flaky backend (seeded RNG) standing in for a real model
  service that sometimes errors.
- `RoutingStrategy` (ABC) - `select(request_id) -> version`, the backend-picking contract.
- `CanaryStrategy` - routes a configurable percentage to the canary version, rest to stable, hashed
  on `request_id` so the same request always picks the same version.
- `WeightedSplitStrategy` - generalizes to N versions with arbitrary weights, same hashing approach.
- `ModelRouter` - asks the strategy for a primary version, then walks `fallback_order` (chain of
  responsibility) if the primary backend raises `ModelError`, returning the first version that
  succeeds.

## Patterns used
- **Strategy** - `RoutingStrategy` implementations are interchangeable traffic-splitting algorithms
  selected at construction time.
- **Chain of Responsibility** - `ModelRouter.route` walks an ordered list of backends, each getting
  a chance to handle the request before falling through to the next.

## How to run
```
cd /Users/bhargav/Desktop/low-level-design/model-router
python3 main.py
```
