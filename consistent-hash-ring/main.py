"""Consistent hash ring - nodes and keys are hashed onto the same circular keyspace; a key belongs
to whichever node's position is the first one clockwise from it. Each physical node gets many
virtual positions on the ring, which is what keeps load even (one point per node would carve the
ring into wildly unequal arcs) and keeps remapping cheap when membership changes (only the keys
between the changed node's positions and its predecessor's move - everyone else's owner is
untouched)."""

import bisect
import hashlib
import statistics
from abc import ABC, abstractmethod
from collections import Counter


class HashFunction(ABC):
    @abstractmethod
    def __call__(self, key: str) -> int:
        ...


class Md5Hash(HashFunction):
    """128-bit hash via md5, plenty of spread for ring positions - not used for anything
    security-sensitive here, just as a stable, well-distributed integer keyspace."""

    def __call__(self, key: str) -> int:
        return int(hashlib.md5(key.encode()).hexdigest(), 16)


class ConsistentHashRing:
    """`hash_fn` picks how points land on the ring (Strategy); the ring itself just keeps a sorted
    list of positions and binary-searches it. `virtual_nodes` per physical node smooths the load
    distribution - more virtual nodes trades a bit of memory for evenness."""

    def __init__(self, hash_fn: HashFunction, virtual_nodes: int = 150):
        self.hash_fn = hash_fn
        self.virtual_nodes = virtual_nodes
        self._ring: dict[int, str] = {}
        self._sorted_positions: list[int] = []
        self._nodes: set[str] = set()

    def add_node(self, node: str):
        self._nodes.add(node)
        for i in range(self.virtual_nodes):
            pos = self.hash_fn(f"{node}#{i}")
            if pos in self._ring:
                continue  # extremely unlikely collision; keep whichever node claimed it first
            self._ring[pos] = node
            bisect.insort(self._sorted_positions, pos)

    def remove_node(self, node: str):
        self._nodes.discard(node)
        for i in range(self.virtual_nodes):
            pos = self.hash_fn(f"{node}#{i}")
            if self._ring.get(pos) != node:
                continue
            del self._ring[pos]
            idx = bisect.bisect_left(self._sorted_positions, pos)
            del self._sorted_positions[idx]

    def get_node(self, key: str) -> str:
        if not self._sorted_positions:
            raise RuntimeError("ring is empty")
        pos = self.hash_fn(key)
        idx = bisect.bisect_right(self._sorted_positions, pos) % len(self._sorted_positions)
        return self._ring[self._sorted_positions[idx]]

    @property
    def nodes(self) -> set[str]:
        return set(self._nodes)


def distribution(ring: ConsistentHashRing, keys: list[str]) -> Counter:
    return Counter(ring.get_node(k) for k in keys)


def main():
    hash_fn = Md5Hash()
    ring = ConsistentHashRing(hash_fn, virtual_nodes=200)

    initial_nodes = [f"cache-{i}" for i in range(5)]
    for n in initial_nodes:
        ring.add_node(n)

    keys = [f"key-{i}" for i in range(20_000)]
    before = {k: ring.get_node(k) for k in keys}

    dist_before = distribution(ring, keys)
    ideal = len(keys) / len(initial_nodes)
    print(f"{len(initial_nodes)} nodes, {len(keys)} keys, ideal ~{ideal:.0f} keys/node")
    print("distribution before adding a node:")
    for node in sorted(dist_before):
        print(f"  {node}: {dist_before[node]:>6}  ({dist_before[node] / ideal:.2f}x ideal)")

    load_ratios = [count / ideal for count in dist_before.values()]
    max_skew = max(abs(r - 1.0) for r in load_ratios)
    print(f"max deviation from ideal: {max_skew:.2%}")

    # Add a 6th node - only keys that now fall between the new node's virtual positions and their
    # ring predecessors should move; everyone else's owner is unchanged.
    ring.add_node("cache-5")
    after = {k: ring.get_node(k) for k in keys}

    moved = sum(1 for k in keys if before[k] != after[k])
    moved_fraction = moved / len(keys)
    expected_fraction = 1 / len(ring.nodes)  # naive expectation: new node claims ~1/N of the keyspace
    print(f"\nafter adding a 6th node: {moved} / {len(keys)} keys moved ({moved_fraction:.2%})")
    print(f"theoretical expectation ~1/{len(ring.nodes)} = {expected_fraction:.2%}")

    # Every key that moved must now point at the new node - consistent hashing never reshuffles
    # a key onto some other pre-existing node, only onto the newcomer.
    moved_to = {after[k] for k in keys if before[k] != after[k]}
    assert moved_to == {"cache-5"}, f"keys moved to unexpected nodes: {moved_to - {'cache-5'}}"

    assert abs(moved_fraction - expected_fraction) < 0.05, (
        f"moved fraction {moved_fraction:.2%} too far from expected {expected_fraction:.2%}"
    )
    assert max_skew < 0.30, f"load distribution too skewed ({max_skew:.2%} max deviation)"

    stdev_before = statistics.pstdev(dist_before.values())
    print(f"\nself-check passed: {moved_fraction:.2%} of keys moved (~1/{len(ring.nodes)} expected), "
          f"all moved keys landed on the new node, and pre-add distribution stayed within "
          f"{max_skew:.0%} of ideal (stdev={stdev_before:.0f} keys).")


if __name__ == "__main__":
    main()
