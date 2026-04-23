# GPU Quota Manager

## Problem
Design a multi-tenant GPU scheduler where each tenant has a weight entitling it to a proportional
share of a fixed pool of GPUs. When the cluster is oversubscribed (tenants collectively want more
than exists), a request from one tenant should be able to reclaim GPUs from a tenant that's
currently holding more than its own fair share - but never take a tenant below what it's entitled
to - instead of simply queuing or rejecting the request.

## Design
- `Tenant` - `tenant_id`, `weight`.
- `PreemptionPolicy` (ABC) - `select_victims(scheduler, requester_id, needed) -> [(victim_id, amount), ...]`.
  - `FairShareExcessPolicy` - only ever reclaims the *surplus* portion of a tenant's allocation
    (`allocated - fair_share`), largest surplus first, so a victim can never be preempted below its
    own entitlement.
- `FairShareScheduler` - `register_tenant`, `fair_share(tenant_id) = total_gpus * (weight /
  total_weight)`, `request(tenant_id, gpus)`. If free capacity covers the request it's granted
  directly; otherwise the policy is asked for victims to cover the shortfall, those GPUs are
  reclaimed (logged as `PreemptionEvent`s), and the request is granted - fully if reclaiming
  covered the shortfall, partially (free + reclaimable) if even preempting every over-share tenant
  isn't enough.
- `jains_fairness_index(ratios)` - the standard `(Σx)² / (n·Σx²)` fairness metric from scheduling
  and networking literature; 1.0 means every tenant's `allocation/weight` ratio is identical
  (perfectly proportional), lower means the split skews away from weights.

## Patterns used
- **Strategy** - `PreemptionPolicy` is the swappable "which tenants get reclaimed from" algorithm;
  `FairShareScheduler` only depends on the interface, so a different admission policy (e.g.
  priority-based instead of fair-share-based) could be dropped in without touching the scheduler.

## How to run
```
cd /Users/bhargav/Desktop/low-level-design/gpu-quota-manager
python3 main.py
```
The demo registers 5 tenants with weights 1/2/2/3/4 over a 24-GPU pool, then has each request 10
GPUs in sequence - deliberately oversubscribing the cluster so later requests must preempt earlier
ones. It asserts every GPU stays accounted for (`sum(allocations) <= total_gpus` after every
request), at least one preemption actually happened, no tenant ever ends up below its own
fair-share floor, and the final `Jain's fairness index` over `allocation/weight` ratios is at least
0.90 (in this scenario it lands at a perfect 1.0000 - every tenant's final allocation is exactly
proportional to its weight).
