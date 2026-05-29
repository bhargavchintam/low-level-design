"""Feature store client demo - an online KV store for low-latency serving and an offline table for
point-in-time-correct training data, behind one client that picks the right retrieval path (Facade)."""

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class FeatureValue:
    value: float
    event_timestamp: datetime


class OnlineStore:
    """Latest-value KV store: entity_id -> {feature_name: FeatureValue}. Serving reads only ever
    see the most recent write, which is what makes it fast and also what makes it capable of being stale."""

    def __init__(self):
        self._table: dict[str, dict[str, FeatureValue]] = {}

    def write(self, entity_id: str, feature_name: str, fv: FeatureValue):
        self._table.setdefault(entity_id, {})[feature_name] = fv

    def read(self, entity_id: str, feature_names: list[str]) -> dict[str, FeatureValue | None]:
        row = self._table.get(entity_id, {})
        return {name: row.get(name) for name in feature_names}


class OfflineStore:
    """Append-only log of (entity_id, feature_name, value, event_timestamp) rows - the full history,
    used to reconstruct what a feature's value was at any point in the past."""

    def __init__(self):
        self._rows: list[tuple[str, str, float, datetime]] = []

    def write(self, entity_id: str, feature_name: str, value: float, event_timestamp: datetime):
        self._rows.append((entity_id, feature_name, value, event_timestamp))

    def point_in_time_lookup(self, entity_id: str, feature_name: str, as_of: datetime) -> float | None:
        """Latest value with event_timestamp <= as_of. Excluding anything after `as_of` is what
        makes a training row point-in-time-correct instead of leaking future information."""
        candidates = [
            (ts, val)
            for (eid, fname, val, ts) in self._rows
            if eid == entity_id and fname == feature_name and ts <= as_of
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda c: c[0])[1]


@dataclass
class FeatureView:
    name: str
    feature_names: list[str]
    max_age: timedelta  # freshness SLA for online serving


class FeatureStoreClient:
    """Facade over the online and offline stores; the caller states intent (serve vs train) and
    the client picks the retrieval path, without exposing either store's internals."""

    def __init__(self, online: OnlineStore, offline: OfflineStore):
        self.online = online
        self.offline = offline

    def get_online_features(self, view: FeatureView, entity_id: str, now: datetime) -> dict:
        """Serving path: latest value per feature, flagged stale if older than the view's max_age."""
        raw = self.online.read(entity_id, view.feature_names)
        result = {}
        for name, fv in raw.items():
            if fv is None:
                result[name] = {"value": None, "stale": True}
            else:
                result[name] = {"value": fv.value, "stale": (now - fv.event_timestamp) > view.max_age}
        return result

    def get_historical_features(
        self, view: FeatureView, entity_timestamps: list[tuple[str, datetime]]
    ) -> list[dict]:
        """Training path: one row per (entity_id, timestamp) pair, each feature resolved as of
        that exact timestamp via a point-in-time join - the same entity can appear with different
        feature values at different rows, matching what was true when each label was generated."""
        out = []
        for entity_id, ts in entity_timestamps:
            row = {"entity_id": entity_id, "event_timestamp": ts}
            for name in view.feature_names:
                row[name] = self.offline.point_in_time_lookup(entity_id, name, ts)
            out.append(row)
        return out


def main():
    online = OnlineStore()
    offline = OfflineStore()
    client = FeatureStoreClient(online, offline)

    view = FeatureView(
        name="user_activity",
        feature_names=["txn_count_7d", "avg_txn_amount"],
        max_age=timedelta(minutes=10),
    )

    # Offline store gets the full history - this is what training reads from.
    history = [
        ("u1", "txn_count_7d", 3, datetime(2024, 1, 1, 8, 0)),
        ("u1", "avg_txn_amount", 42.0, datetime(2024, 1, 1, 8, 0)),
        ("u1", "txn_count_7d", 5, datetime(2024, 1, 3, 9, 0)),
        ("u1", "avg_txn_amount", 55.5, datetime(2024, 1, 3, 9, 0)),
        ("u1", "txn_count_7d", 9, datetime(2024, 1, 6, 10, 0)),
        ("u1", "avg_txn_amount", 61.0, datetime(2024, 1, 6, 10, 0)),
    ]
    for entity_id, feature_name, value, ts in history:
        offline.write(entity_id, feature_name, value, ts)

    # Online store only holds the latest snapshot - this is what serving reads from.
    online.write("u1", "txn_count_7d", FeatureValue(9, datetime(2024, 1, 6, 10, 0)))
    online.write("u1", "avg_txn_amount", FeatureValue(61.0, datetime(2024, 1, 6, 10, 0)))

    print("-- serving fetch: online store, freshness checked against now --")
    fresh_now = datetime(2024, 1, 6, 10, 5)
    print(f"now={fresh_now}")
    for name, info in client.get_online_features(view, "u1", fresh_now).items():
        print(f"  {name}: {info}")

    stale_now = datetime(2024, 1, 6, 10, 45)
    print(f"\nnow={stale_now} (past the 10-minute freshness SLA)")
    for name, info in client.get_online_features(view, "u1", stale_now).items():
        print(f"  {name}: {info}")

    print("\n-- training fetch: offline store, point-in-time join per labeled row --")
    entity_timestamps = [
        ("u1", datetime(2024, 1, 2, 0, 0)),   # between the 1/1 and 1/3 writes
        ("u1", datetime(2024, 1, 4, 0, 0)),   # between the 1/3 and 1/6 writes
        ("u1", datetime(2024, 1, 6, 10, 0)),  # exactly at the latest write
    ]
    for row in client.get_historical_features(view, entity_timestamps):
        print(f"  {row}")


if __name__ == "__main__":
    main()
