"""Priority scheduler - a heap-based job queue with priority aging so a low-priority job
submitted early can't starve forever behind an endless stream of higher-priority arrivals.
heapq has no decrease-key, so promoting a waiting job's priority uses the standard lazy-
deletion trick: push a fresh entry carrying the job's current version, and silently drop
any popped entry whose version no longer matches the job's latest version.
"""

import heapq
import itertools
from dataclasses import dataclass, field

HIGHEST = 0  # lower number = higher priority, so a min-heap pops the most urgent job first


@dataclass
class Job:
    job_id: str
    base_priority: int
    submit_tick: int
    priority: int = field(init=False)
    last_boost_tick: int = field(init=False)
    version: int = 0
    completed_tick: int | None = None

    def __post_init__(self):
        self.priority = self.base_priority
        self.last_boost_tick = self.submit_tick

    @property
    def wait(self) -> int | None:
        return None if self.completed_tick is None else self.completed_tick - self.submit_tick


class PriorityScheduler:
    """Min-heap of (priority, seq, version, job_id): lower priority number runs first,
    seq (a monotonic counter) breaks ties FIFO. age(now) promotes any still-waiting job
    that hasn't been boosted in `aging_interval` ticks and pushes a new heap entry for
    it - the old entry is left in the heap as a stale duplicate, discarded on sight by
    run_next() instead of ever being scheduled."""

    def __init__(self, aging_interval: int | None):
        self.aging_interval = aging_interval
        self._heap: list[tuple[int, int, int, str]] = []
        self._seq = itertools.count()
        self._jobs: dict[str, Job] = {}
        self._waiting: set[str] = set()
        self.completed: list[Job] = []

    def submit(self, job_id: str, priority: int, tick: int):
        job = Job(job_id, priority, tick)
        self._jobs[job_id] = job
        self._waiting.add(job_id)
        self._push(job)

    def _push(self, job: Job):
        heapq.heappush(self._heap, (job.priority, next(self._seq), job.version, job.job_id))

    def age(self, now: int):
        if self.aging_interval is None:
            return
        for job_id in self._waiting:
            job = self._jobs[job_id]
            if job.priority > HIGHEST and now - job.last_boost_tick >= self.aging_interval:
                job.priority -= 1
                job.last_boost_tick = now
                job.version += 1
                self._push(job)

    def run_next(self, now: int) -> Job | None:
        while self._heap:
            priority, seq, version, job_id = heapq.heappop(self._heap)
            job = self._jobs[job_id]
            if job_id not in self._waiting or version != job.version:
                continue  # superseded by a later promotion - not the job's current entry
            self._waiting.discard(job_id)
            job.completed_tick = now
            self.completed.append(job)
            return job
        return None

    def waiting_ids(self) -> set[str]:
        return set(self._waiting)


def run_simulation(aging_interval: int | None, num_ticks: int) -> PriorityScheduler:
    """One low-priority job L submitted at tick 0, then a fresh high-priority job every
    tick after - the classic starvation setup: without aging, L never wins a priority
    comparison against a same-or-later arrival that's always strictly more urgent."""
    sched = PriorityScheduler(aging_interval)
    sched.submit("L", priority=3, tick=0)
    sched.submit("H-0", priority=HIGHEST, tick=0)

    for tick in range(num_ticks):
        if tick > 0:
            sched.submit(f"H-{tick}", priority=HIGHEST, tick=tick)
        sched.age(tick)
        sched.run_next(tick)

    return sched


def main():
    num_ticks = 40
    aging_interval = 5

    print(f"scenario: job L (priority 3) submitted at tick 0, then one priority-0 job "
          f"every tick for {num_ticks} ticks; exactly one job runs per tick.\n")

    fair = run_simulation(aging_interval, num_ticks)
    unfair = run_simulation(None, num_ticks)

    l_fair = next(j for j in fair.completed if j.job_id == "L")
    print(f"with aging (interval={aging_interval}): L completed at tick {l_fair.completed_tick} "
          f"(waited {l_fair.wait} ticks), final priority {l_fair.priority}")
    print(f"  still waiting at end: {sorted(fair.waiting_ids())[:3]}{'...' if len(fair.waiting_ids()) > 3 else ''} "
          f"({len(fair.waiting_ids())} jobs)")

    print(f"\nwithout aging: L {'completed' if 'L' in [j.job_id for j in unfair.completed] else 'is still waiting'} "
          f"after {num_ticks} ticks ({len(unfair.completed)} jobs completed total, all high-priority)")

    max_wait = max(j.wait for j in fair.completed)
    print(f"\nlongest wait among all completed jobs (aging run): {max_wait} ticks")

    # Aging must actually rescue L: it has to complete, and its promoted priority must
    # have reached HIGHEST (0) - three promotions of one level each from a base of 3.
    assert l_fair.completed_tick is not None
    assert l_fair.priority == HIGHEST

    # Aging bounds worst-case wait: L needed 3 promotions at `aging_interval` ticks
    # apart, so it can't plausibly still be waiting past 3*aging_interval + a small
    # scheduling slack for the tick it actually wins its priority tie.
    assert l_fair.wait <= 3 * aging_interval + 2, f"L waited {l_fair.wait} ticks - aging isn't bounding starvation"

    # Without aging, the same job under the same arrival pattern must NOT complete -
    # the direct contrast that proves aging (not luck) is what rescued it above.
    assert "L" not in [j.job_id for j in unfair.completed], "L completed even without aging - scenario isn't testing starvation"
    assert "L" in unfair.waiting_ids()

    # No completed job in the aging run waited longer than L - L was the starvation
    # risk, so nothing else should have been starved worse while it got promoted.
    assert max_wait == l_fair.wait

    print(f"\nself-check passed: aging promoted L to priority {HIGHEST} and rescued it in "
          f"{l_fair.wait} ticks (bounded, as expected); the identical workload with aging "
          f"disabled left L starved for the entire {num_ticks}-tick run.")


if __name__ == "__main__":
    main()
