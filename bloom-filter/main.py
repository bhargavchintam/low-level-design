"""Bloom filter - a space-efficient probabilistic set. Adding an item flips k bits (derived from
its hash) in an m-bit array; querying checks whether all k of those bits are set. A "no" is always
correct (a clear bit proves the item was never added); a "yes" might be a false positive caused by
other items' bits happening to cover the same k positions. m and k are sized from the expected
item count and a target false-positive rate using the standard closed-form formulas."""

import hashlib
import math
from abc import ABC, abstractmethod

import numpy as np


class HashFamily(ABC):
    @abstractmethod
    def positions(self, item: str, m: int, k: int) -> np.ndarray:
        """Return k bit positions in [0, m) for item."""


class DoubleHashingFamily(HashFamily):
    """Kirsch-Mitzenmacher double hashing: derive k hash values from just two real hashes via
    h_i(x) = h1(x) + i*h2(x), instead of computing k genuinely independent hash functions. Proven
    to give false-positive rates statistically indistinguishable from using k independent hashes,
    and it's what real Bloom filter implementations (e.g. Guava's) actually do."""

    def positions(self, item: str, m: int, k: int) -> np.ndarray:
        digest = hashlib.sha256(item.encode()).digest()
        h1 = int.from_bytes(digest[:16], "big")
        h2 = int.from_bytes(digest[16:], "big")
        return np.array([(h1 + i * h2) % m for i in range(k)], dtype=np.int64)


class BloomFilter:
    def __init__(self, capacity: int, false_positive_rate: float, hash_family: HashFamily | None = None):
        self.capacity = capacity
        self.target_fp_rate = false_positive_rate
        self.hash_family = hash_family or DoubleHashingFamily()

        # Standard sizing formulas: m minimizes bit-array size for the target fp rate at this
        # capacity; k is the number of hashes that minimizes the fp rate for that m and n.
        self.m = max(1, math.ceil(-(capacity * math.log(false_positive_rate)) / (math.log(2) ** 2)))
        self.k = max(1, round((self.m / capacity) * math.log(2)))

        self._bits = np.zeros(self.m, dtype=bool)
        self.count = 0

    def add(self, item: str):
        positions = self.hash_family.positions(item, self.m, self.k)
        self._bits[positions] = True
        self.count += 1

    def __contains__(self, item: str) -> bool:
        positions = self.hash_family.positions(item, self.m, self.k)
        return bool(np.all(self._bits[positions]))

    def estimated_false_positive_rate(self) -> float:
        """(1 - e^(-k*n/m))^k - the textbook estimate given how many bits are actually set,
        using the real insert count n rather than the design-time capacity."""
        return (1 - math.exp(-self.k * self.count / self.m)) ** self.k

    def load_factor(self) -> float:
        return float(self._bits.mean())


def main():
    n_items = 5_000
    target_fp = 0.01
    bf = BloomFilter(capacity=n_items, false_positive_rate=target_fp)
    print(f"capacity={n_items}, target_fp={target_fp}  ->  m={bf.m} bits, k={bf.k} hashes "
          f"({bf.m / n_items:.1f} bits/item)")

    inserted = [f"user:{i}" for i in range(n_items)]
    for item in inserted:
        bf.add(item)

    # No false negatives: every inserted item must test positive, always.
    false_negatives = sum(1 for item in inserted if item not in bf)
    assert false_negatives == 0, f"{false_negatives} false negatives found - filter is broken"

    # Measure the false-positive rate on a disjoint set of keys that were never inserted.
    n_probe = 200_000
    absent = [f"absent:{i}" for i in range(n_probe)]
    false_positives = sum(1 for item in absent if item in bf)
    measured_fp = false_positives / n_probe
    estimated_fp = bf.estimated_false_positive_rate()

    print(f"load factor (bits set): {bf.load_factor():.2%}")
    print(f"false negatives on {n_items} inserted items: {false_negatives}")
    print(f"false positives on {n_probe} absent items: {false_positives} (measured rate {measured_fp:.4f})")
    print(f"theoretical estimate: {estimated_fp:.4f}  |  design target: {target_fp}")

    assert measured_fp < target_fp * 2.5, (
        f"measured fp rate {measured_fp:.4f} far exceeds target {target_fp} - hashing/sizing is off"
    )
    assert abs(measured_fp - estimated_fp) < target_fp, (
        f"measured fp rate {measured_fp:.4f} doesn't track the theoretical estimate {estimated_fp:.4f}"
    )

    print(f"\nself-check passed: zero false negatives across {n_items} inserted items, and the "
          f"measured false-positive rate ({measured_fp:.4f}) tracks both the {target_fp} design "
          f"target and the {estimated_fp:.4f} theoretical estimate.")


if __name__ == "__main__":
    main()
