"""LLM rate limiter - token-bucket limiting keyed on both requests/min and tokens/min. A call is
throttled if it would exceed either limit, even when the other still has headroom."""

from dataclasses import dataclass


class FakeClock:
    """Controllable clock so the demo is deterministic instead of sleeping real time."""

    def __init__(self):
        self._now = 0.0

    def time(self) -> float:
        return self._now

    def advance(self, seconds: float):
        self._now += seconds


class TokenBucket:
    """Generic bucket of `capacity` units, refilling continuously at `refill_rate` units/sec."""

    def __init__(self, capacity: float, refill_rate: float, clock: FakeClock):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.clock = clock
        self._units = float(capacity)
        self._last_refill = clock.time()

    def _refill(self):
        now = self.clock.time()
        elapsed = now - self._last_refill
        if elapsed > 0:
            self._units = min(self.capacity, self._units + elapsed * self.refill_rate)
            self._last_refill = now

    def available(self) -> float:
        self._refill()
        return self._units

    def consume(self, amount: float):
        self._units -= amount


@dataclass
class Decision:
    allowed: bool
    reason: str = "ok"


class LlmRateLimiter:
    """Per-client pair of buckets, one for request count (RPM) and one for token count (TPM).
    Both are checked for headroom before either is debited, so a rejection never partially
    consumes a bucket the request wasn't actually allowed to use."""

    def __init__(self, requests_per_minute: int, tokens_per_minute: int, clock: FakeClock):
        self.rpm = requests_per_minute
        self.tpm = tokens_per_minute
        self.clock = clock
        self._request_buckets: dict[str, TokenBucket] = {}
        self._token_buckets: dict[str, TokenBucket] = {}

    def _buckets(self, client_id: str) -> tuple[TokenBucket, TokenBucket]:
        if client_id not in self._request_buckets:
            self._request_buckets[client_id] = TokenBucket(self.rpm, self.rpm / 60.0, self.clock)
            self._token_buckets[client_id] = TokenBucket(self.tpm, self.tpm / 60.0, self.clock)
        return self._request_buckets[client_id], self._token_buckets[client_id]

    def allow_request(self, client_id: str, tokens_requested: int) -> Decision:
        request_bucket, token_bucket = self._buckets(client_id)
        if request_bucket.available() < 1:
            return Decision(False, "requests/min limit exceeded")
        if token_bucket.available() < tokens_requested:
            return Decision(False, "tokens/min limit exceeded")
        request_bucket.consume(1)
        token_bucket.consume(tokens_requested)
        return Decision(True)


def run_demo(clock: FakeClock, limiter: LlmRateLimiter, calls: list[tuple[float, int]]):
    for i, (advance, tokens) in enumerate(calls, start=1):
        clock.advance(advance)
        decision = limiter.allow_request("client-1", tokens)
        status = "ALLOW" if decision.allowed else f"THROTTLE ({decision.reason})"
        print(f"call {i:>2} @ t={clock.time():>5.1f}s  tokens_requested={tokens:<5} -> {status}")


def main():
    # capacity=5 requests/min, 2000 tokens/min - small limits so both dimensions get exercised.
    clock = FakeClock()
    limiter = LlmRateLimiter(requests_per_minute=5, tokens_per_minute=2000, clock=clock)

    print("-- burst of large-token calls: trips the TPM limit before RPM --")
    run_demo(clock, limiter, [(0, 900), (0, 900), (0, 900)])

    print("\n-- burst of small-token calls: trips the RPM limit instead --")
    clock2 = FakeClock()
    limiter2 = LlmRateLimiter(requests_per_minute=5, tokens_per_minute=2000, clock=clock2)
    run_demo(clock2, limiter2, [(0, 10)] * 7)

    print("\n-- recovery after waiting for refill --")
    run_demo(clock2, limiter2, [(30, 10), (30, 10)])


if __name__ == "__main__":
    main()
