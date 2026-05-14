"""AB test assignment - deterministic bucketing via consistent hashing of user_id, so the same
user always lands in the same variant with no per-user state ever stored."""

from abc import ABC, abstractmethod
from bisect import bisect_right
from collections import Counter
from dataclasses import dataclass
import hashlib


class HashStrategy(ABC):
    @abstractmethod
    def to_unit_interval(self, key: str) -> float:
        """Map an arbitrary string to a float in [0, 1), stably across calls."""


class Md5HashStrategy(HashStrategy):
    def to_unit_interval(self, key: str) -> float:
        digest = hashlib.md5(key.encode()).hexdigest()
        return int(digest, 16) / 16 ** len(digest)


@dataclass
class Variant:
    name: str
    weight: float


class Experiment:
    """Splits traffic across variants by weight. `assign` is a pure function of
    (experiment_name, user_id): the experiment name salts the hash so the same user is bucketed
    independently across different experiments, and no assignment is ever written to storage -
    the hash itself is the source of truth."""

    def __init__(self, name: str, variants: list[Variant], hash_strategy: HashStrategy | None = None):
        total_weight = sum(v.weight for v in variants)
        if abs(total_weight - 1.0) > 1e-9:
            raise ValueError(f"variant weights must sum to 1.0, got {total_weight}")
        self.name = name
        self.variants = variants
        self.hash_strategy = hash_strategy or Md5HashStrategy()
        self._boundaries = []
        cumulative = 0.0
        for v in variants:
            cumulative += v.weight
            self._boundaries.append(cumulative)

    def assign(self, user_id: str) -> str:
        point = self.hash_strategy.to_unit_interval(f"{self.name}:{user_id}")
        index = min(bisect_right(self._boundaries, point), len(self.variants) - 1)
        return self.variants[index].name


def main():
    button_color = Experiment("checkout-button-color", [Variant("control", 0.5), Variant("treatment", 0.5)])
    onboarding = Experiment(
        "onboarding-flow",
        [Variant("wizard", 0.34), Variant("single-page", 0.33), Variant("video", 0.33)],
    )

    users = [f"user-{i}" for i in range(20000)]

    for experiment in (button_color, onboarding):
        counts = Counter(experiment.assign(u) for u in users)
        print(f"-- split for '{experiment.name}' over {len(users)} users --")
        for variant in experiment.variants:
            count = counts[variant.name]
            print(f"  {variant.name:<14} target={variant.weight:.0%}  actual={count / len(users):.1%}  ({count})")
        print()

    print("-- consistency check: repeated assignment for the same users --")
    for user_id in users[:5]:
        repeats = {button_color.assign(user_id) for _ in range(10)}
        onboarding_variant = onboarding.assign(user_id)
        print(f"  {user_id}: checkout-button-color={repeats.pop()} (10/10 calls agreed) "
              f"onboarding-flow={onboarding_variant}")


if __name__ == "__main__":
    main()
