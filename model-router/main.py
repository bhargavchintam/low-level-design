"""Model router - routes inference requests across model versions via a pluggable routing strategy
(canary %, weighted A/B split), falling back to another backend when the chosen one errors."""

from abc import ABC, abstractmethod
import hashlib
import random


class ModelError(Exception):
    pass


class ModelBackend(ABC):
    @abstractmethod
    def predict(self, request_id: str) -> str:
        ...


class SimpleModelBackend(ModelBackend):
    """Deterministically flaky backend - fails a fixed fraction of calls, seeded for repeatability."""

    def __init__(self, version: str, failure_rate: float = 0.0, seed: int = 0):
        self.version = version
        self.failure_rate = failure_rate
        self._rng = random.Random(seed)

    def predict(self, request_id: str) -> str:
        if self._rng.random() < self.failure_rate:
            raise ModelError(f"{self.version} failed on {request_id}")
        return f"prediction-from-{self.version}"


def _to_unit_interval(key: str) -> float:
    digest = hashlib.md5(key.encode()).hexdigest()
    return int(digest, 16) / 16 ** len(digest)


class RoutingStrategy(ABC):
    @abstractmethod
    def select(self, request_id: str) -> str:
        """Return the backend version name to try first for this request."""


class CanaryStrategy(RoutingStrategy):
    """Sends a fixed percentage of traffic to the canary version, the rest to stable - hashed on
    request_id so retries of the same request are consistently routed to the same version."""

    def __init__(self, stable: str, canary: str, canary_percent: float):
        self.stable = stable
        self.canary = canary
        self.canary_percent = canary_percent

    def select(self, request_id: str) -> str:
        point = _to_unit_interval(f"canary:{request_id}")
        return self.canary if point < self.canary_percent else self.stable


class WeightedSplitStrategy(RoutingStrategy):
    """A/B split across N versions by weight, consistently hashed per request_id."""

    def __init__(self, weights: dict[str, float]):
        if abs(sum(weights.values()) - 1.0) > 1e-9:
            raise ValueError("weights must sum to 1.0")
        self.versions = list(weights.keys())
        self._boundaries = []
        cumulative = 0.0
        for version in self.versions:
            cumulative += weights[version]
            self._boundaries.append(cumulative)

    def select(self, request_id: str) -> str:
        point = _to_unit_interval(f"split:{request_id}")
        for version, boundary in zip(self.versions, self._boundaries):
            if point < boundary:
                return version
        return self.versions[-1]


class ModelRouter:
    """Picks a backend via the routing strategy, then falls back through `fallback_order` (chain of
    responsibility) if the chosen backend raises `ModelError`."""

    def __init__(self, backends: dict[str, ModelBackend], strategy: RoutingStrategy, fallback_order: list[str]):
        self.backends = backends
        self.strategy = strategy
        self.fallback_order = fallback_order

    def route(self, request_id: str) -> tuple[str, str]:
        primary = self.strategy.select(request_id)
        chain = [primary] + [v for v in self.fallback_order if v != primary]
        last_error = None
        for version in chain:
            try:
                return version, self.backends[version].predict(request_id)
            except ModelError as e:
                last_error = e
        raise RuntimeError(f"all backends failed for {request_id}: {last_error}")


def main():
    print("-- canary rollout: 20% of traffic to a flaky canary, rest to stable --")
    stable = SimpleModelBackend("v1-stable", failure_rate=0.0)
    canary = SimpleModelBackend("v2-canary", failure_rate=0.4, seed=7)
    router = ModelRouter(
        backends={"v1-stable": stable, "v2-canary": canary},
        strategy=CanaryStrategy(stable="v1-stable", canary="v2-canary", canary_percent=0.2),
        fallback_order=["v1-stable", "v2-canary"],
    )

    served_by = []
    fallback_examples = []
    for i in range(200):
        request_id = f"req-{i}"
        primary_pick = router.strategy.select(request_id)
        version, _ = router.route(request_id)
        served_by.append(version)
        if version != primary_pick:
            fallback_examples.append(f"{request_id}: routed to {primary_pick}, failed over to {version}")

    print(f"  served by v1-stable: {served_by.count('v1-stable')}, v2-canary: {served_by.count('v2-canary')}")
    print(f"  fallbacks triggered: {len(fallback_examples)}")
    for line in fallback_examples[:5]:
        print(f"    {line}")

    print("\n-- weighted A/B split across three versions --")
    backends = {
        "v1": SimpleModelBackend("v1", failure_rate=0.0),
        "v2": SimpleModelBackend("v2", failure_rate=0.0),
        "v3": SimpleModelBackend("v3", failure_rate=0.0),
    }
    split_router = ModelRouter(
        backends=backends,
        strategy=WeightedSplitStrategy({"v1": 0.5, "v2": 0.3, "v3": 0.2}),
        fallback_order=["v1", "v2", "v3"],
    )
    tally = {"v1": 0, "v2": 0, "v3": 0}
    n = 5000
    for i in range(n):
        version, _ = split_router.route(f"user-{i}")
        tally[version] += 1
    for version, count in tally.items():
        print(f"  {version}: {count / n:.1%}")


if __name__ == "__main__":
    main()
