# Feature Store Client

## Problem
Design a client that serves ML features two different ways: low-latency lookup of the latest value
for online inference, and point-in-time-correct historical lookup for building training data. The
training path must never leak a feature value that didn't exist yet as of the label's timestamp, and
the serving path must be able to tell the caller when a feature is stale.

## Design
- `FeatureValue` - a value plus the timestamp it was computed at.
- `OnlineStore` - KV store keyed by `entity_id`, holding only the latest `FeatureValue` per feature.
  Fast reads, no history.
- `OfflineStore` - append-only log of every `(entity_id, feature_name, value, event_timestamp)` row
  ever written. `point_in_time_lookup` returns the latest value with `event_timestamp <= as_of`,
  which is what prevents training rows from seeing the future.
- `FeatureView` - names a group of features served together, plus a `max_age` freshness SLA for the
  online path.
- `FeatureStoreClient` - facade over both stores; `get_online_features` reads the latest snapshot and
  flags anything older than `max_age` as stale, `get_historical_features` runs the point-in-time join
  for a list of `(entity_id, timestamp)` pairs.

## Patterns used
- **Facade** - `FeatureStoreClient` hides the two-store split behind two intent-based methods, so
  callers ask for "online" or "historical" features without knowing how each is stored.

## How to run
```
cd /Users/bhargav/Desktop/low-level-design/feature-store-client
python3 main.py
```
