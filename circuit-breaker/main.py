"""Circuit breaker for calls to a flaky service - State pattern over closed/open/half-open, each
state deciding whether to let a call through and how to react to its outcome."""

from abc import ABC, abstractmethod


class FakeClock:
    """Controllable clock so the demo is deterministic instead of sleeping real time."""

    def __init__(self):
        self._now = 0.0

    def time(self) -> float:
        return self._now

    def advance(self, seconds: float):
        self._now += seconds


class CircuitOpenError(Exception):
    pass


class CircuitState(ABC):
    def on_enter(self, breaker: "CircuitBreaker"):
        pass

    @abstractmethod
    def allow_request(self, breaker: "CircuitBreaker") -> bool:
        ...

    @abstractmethod
    def on_success(self, breaker: "CircuitBreaker"):
        ...

    @abstractmethod
    def on_failure(self, breaker: "CircuitBreaker"):
        ...


class ClosedState(CircuitState):
    """Normal operation - calls pass through; enough consecutive failures trips to Open."""

    def allow_request(self, breaker: "CircuitBreaker") -> bool:
        return True

    def on_success(self, breaker: "CircuitBreaker"):
        breaker.consecutive_failures = 0

    def on_failure(self, breaker: "CircuitBreaker"):
        breaker.consecutive_failures += 1
        if breaker.consecutive_failures >= breaker.failure_threshold:
            breaker.transition_to(OpenState())


class OpenState(CircuitState):
    """Rejects every call immediately, without touching the underlying service, until
    `recovery_timeout` has elapsed - then allows a single trial call through."""

    def __init__(self):
        self._opened_at = None

    def on_enter(self, breaker: "CircuitBreaker"):
        self._opened_at = breaker.clock.time()

    def allow_request(self, breaker: "CircuitBreaker") -> bool:
        if breaker.clock.time() - self._opened_at >= breaker.recovery_timeout:
            breaker.transition_to(HalfOpenState())
            return breaker.state.allow_request(breaker)
        return False

    def on_success(self, breaker: "CircuitBreaker"):
        pass

    def on_failure(self, breaker: "CircuitBreaker"):
        pass


class HalfOpenState(CircuitState):
    """Allows a single trial call through - success closes the circuit, failure reopens it."""

    def allow_request(self, breaker: "CircuitBreaker") -> bool:
        return True

    def on_success(self, breaker: "CircuitBreaker"):
        breaker.consecutive_failures = 0
        breaker.transition_to(ClosedState())

    def on_failure(self, breaker: "CircuitBreaker"):
        breaker.transition_to(OpenState())


class CircuitBreaker:
    def __init__(self, failure_threshold: int, recovery_timeout: float, clock: FakeClock):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.clock = clock
        self.consecutive_failures = 0
        self.state: CircuitState = ClosedState()

    def transition_to(self, state: CircuitState):
        self.state = state
        state.on_enter(self)

    def call(self, func, *args, **kwargs):
        if not self.state.allow_request(self):
            raise CircuitOpenError(f"circuit open, rejecting call (state={type(self.state).__name__})")
        try:
            result = func(*args, **kwargs)
        except Exception:
            self.state.on_failure(self)
            raise
        else:
            self.state.on_success(self)
            return result


class ScriptedService:
    """Test double whose calls succeed or fail according to a scripted sequence, standing in for
    a real flaky downstream model service."""

    def __init__(self, script: list[bool]):
        self._script = iter(script)

    def call(self):
        if not next(self._script):
            raise RuntimeError("service unavailable")
        return "ok"


def main():
    clock = FakeClock()
    breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=5.0, clock=clock)
    service = ScriptedService([True, False, False, False, True, True])

    def attempt(label: str):
        clock.advance(1.0)
        try:
            result = breaker.call(service.call)
            print(f"{label}: OK ({result})  state={type(breaker.state).__name__}")
        except CircuitOpenError as e:
            print(f"{label}: REJECTED ({e})  state={type(breaker.state).__name__}")
        except RuntimeError as e:
            print(f"{label}: FAILED ({e})  state={type(breaker.state).__name__}")

    attempt("call 1 (success)")
    attempt("call 2 (fail)")
    attempt("call 3 (fail)")
    attempt("call 4 (fail -> trips breaker)")
    attempt("call 5 (breaker open, rejected without touching the service)")

    print(f"\nwaiting {breaker.recovery_timeout}s for the recovery timeout to elapse...")
    clock.advance(breaker.recovery_timeout)

    attempt("call 6 (half-open trial, succeeds -> closes)")
    attempt("call 7 (closed, succeeds)")


if __name__ == "__main__":
    main()
