"""Multi-tenant GPU quota manager - each tenant has a weight; its fair share of the cluster is
total_gpus * (weight / sum(all weights)), the same weighted proportional-share idea OS CPU
schedulers and YARN's fair scheduler use for CPU/memory. When a request can't be satisfied from
free capacity alone, the scheduler preempts GPUs from tenants currently holding more than their
own fair share - never taking a tenant below its own entitlement - until either enough is freed or
there's nothing left to reclaim."""

from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class Tenant:
    tenant_id: str
    weight: float


@dataclass
class PreemptionEvent:
    victim: str
    beneficiary: str
    gpus_reclaimed: int


@dataclass
class RequestResult:
    tenant_id: str
    granted: int
    preempted: list[PreemptionEvent] = field(default_factory=list)


class PreemptionPolicy(ABC):
    @abstractmethod
    def select_victims(self, scheduler: "FairShareScheduler", requester_id: str, needed: int
                        ) -> list[tuple[str, int]]:
        """Return [(victim_tenant_id, gpus_to_reclaim), ...] summing to at most `needed`."""


class FairShareExcessPolicy(PreemptionPolicy):
    """Only ever reclaims the portion of a tenant's allocation that exceeds that tenant's own
    fair share - a tenant can never be preempted down below what it's entitled to. Victims with
    the largest surplus (most over their fair share) are reclaimed from first."""

    def select_victims(self, scheduler: "FairShareScheduler", requester_id: str, needed: int
                        ) -> list[tuple[str, int]]:
        surpluses = []
        for tid, allocated in scheduler.allocations.items():
            if tid == requester_id:
                continue
            surplus = allocated - scheduler.fair_share(tid)
            if surplus > 0:
                surpluses.append((tid, surplus))
        surpluses.sort(key=lambda pair: -pair[1])  # largest surplus first

        victims = []
        remaining = needed
        for tid, surplus in surpluses:
            if remaining <= 0:
                break
            take = min(remaining, int(surplus))
            if take > 0:
                victims.append((tid, take))
                remaining -= take
        return victims


class FairShareScheduler:
    def __init__(self, total_gpus: int, policy: PreemptionPolicy | None = None):
        self.total_gpus = total_gpus
        self.policy = policy or FairShareExcessPolicy()
        self.tenants: dict[str, Tenant] = {}
        self.allocations: dict[str, int] = defaultdict(int)
        self.log: list[PreemptionEvent] = []

    def register_tenant(self, tenant_id: str, weight: float):
        self.tenants[tenant_id] = Tenant(tenant_id, weight)

    def fair_share(self, tenant_id: str) -> float:
        total_weight = sum(t.weight for t in self.tenants.values())
        return self.total_gpus * (self.tenants[tenant_id].weight / total_weight)

    def free_capacity(self) -> int:
        return self.total_gpus - sum(self.allocations.values())

    def request(self, tenant_id: str, gpus: int) -> RequestResult:
        free = self.free_capacity()
        if free >= gpus:
            self.allocations[tenant_id] += gpus
            return RequestResult(tenant_id, granted=gpus)

        shortfall = gpus - free
        victims = self.policy.select_victims(self, tenant_id, shortfall)
        reclaimable = sum(amount for _, amount in victims)
        if free + reclaimable < gpus:
            # Not enough reclaimable even after preempting every over-share tenant - grant what's
            # actually achievable (free capacity plus whatever could be reclaimed) rather than
            # nothing, mirroring how a real scheduler grants a partial allocation.
            grant = free + reclaimable
        else:
            grant = gpus

        events = []
        for victim_id, amount in victims:
            self.allocations[victim_id] -= amount
            events.append(PreemptionEvent(victim_id, tenant_id, amount))
            self.log.append(events[-1])

        self.allocations[tenant_id] += grant
        return RequestResult(tenant_id, granted=grant, preempted=events)

    def release(self, tenant_id: str, gpus: int):
        self.allocations[tenant_id] = max(0, self.allocations[tenant_id] - gpus)


def jains_fairness_index(ratios: list[float]) -> float:
    """(sum(x))^2 / (n * sum(x^2)), the standard fairness metric from networking/scheduling
    literature - 1.0 means every tenant got exactly its allocation/weight ratio equalized
    (perfectly fair), lower means some got proportionally more than others."""
    n = len(ratios)
    return (sum(ratios) ** 2) / (n * sum(r ** 2 for r in ratios))


def main():
    total_gpus = 24
    scheduler = FairShareScheduler(total_gpus)

    tenants = [("team-a", 1), ("team-b", 2), ("team-c", 2), ("team-d", 3), ("team-e", 4)]
    for tid, weight in tenants:
        scheduler.register_tenant(tid, weight)

    print(f"{total_gpus} GPUs across {len(tenants)} tenants (weights: "
          f"{', '.join(f'{t}={w}' for t, w in tenants)})")
    print(f"{'tenant':<10}{'fair share':>12}")
    for tid, _ in tenants:
        print(f"{tid:<10}{scheduler.fair_share(tid):>12.2f}")

    # Every tenant asks for far more than its fair share - the cluster is oversubscribed by
    # design, which is what forces preemption to kick in once free capacity runs out.
    print("\nrequests (each tenant asks for 10 GPUs, in order):")
    for tid, _ in tenants:
        result = scheduler.request(tid, 10)
        note = ""
        if result.preempted:
            note = "  preempted: " + ", ".join(
                f"{e.gpus_reclaimed} from {e.victim}" for e in result.preempted
            )
        print(f"  {tid} requested 10, granted {result.granted}{note}")
        assert sum(scheduler.allocations.values()) <= total_gpus, "over-allocated total capacity"

    print(f"\nfinal allocations (total={sum(scheduler.allocations.values())}/{total_gpus}):")
    ratios = []
    for tid, _ in tenants:
        allocated = scheduler.allocations[tid]
        fair = scheduler.fair_share(tid)
        ratio = allocated / scheduler.tenants[tid].weight
        ratios.append(ratio)
        print(f"  {tid}: allocated={allocated:>2}  fair_share={fair:>5.2f}  allocated/weight={ratio:.3f}")

    fairness = jains_fairness_index(ratios)
    print(f"\nJain's fairness index over allocation/weight ratios: {fairness:.4f} (1.0 = perfectly fair)")

    assert len(scheduler.log) > 0, "no preemption ever happened - scenario didn't oversubscribe capacity"
    assert sum(scheduler.allocations.values()) == total_gpus, "capacity left unallocated despite oversubscription"

    # No victim should ever have been pushed below its own fair-share floor. The policy only ever
    # reclaims surplus above fair_share at the moment of preemption; check the final state agrees.
    for tid, _ in tenants:
        floor = scheduler.fair_share(tid)
        # Allow a small integer-rounding slack: fair shares are fractional, allocations are integer GPUs.
        assert scheduler.allocations[tid] >= floor - 1.001, (
            f"{tid} ended up below its fair-share floor: {scheduler.allocations[tid]} < {floor:.2f}"
        )

    assert fairness >= 0.90, f"fairness index {fairness:.4f} too low - allocation isn't weight-proportional"

    print(f"\nself-check passed: {len(scheduler.log)} preemption(s) occurred, all {total_gpus} GPUs "
          f"allocated, no tenant pushed below its fair-share floor, and Jain's fairness index "
          f"({fairness:.4f}) shows allocation tracks weight closely.")


if __name__ == "__main__":
    main()
