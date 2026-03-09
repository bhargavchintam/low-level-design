"""Kernel dispatcher - a registry that picks which concrete kernel implementation runs
for an op, keyed by (op name, dtype, backend). Same shape as how PyTorch/XLA route an
`add` or `matmul` call to one of dozens of compiled kernels depending on the tensor's
dtype and device. Adding a specialized kernel is a decorator, never another branch in
an if/elif chain inside the op itself - and a dtype with no specialized kernel falls
back to that backend's generic implementation instead of crashing outright.
"""

import numpy as np
from dataclasses import dataclass
from enum import Enum


class Backend(Enum):
    CPU = "cpu"
    GPU = "gpu"  # simulated: a vectorized numpy path standing in for a real device kernel


class DispatchError(Exception):
    pass


@dataclass(frozen=True)
class DispatchRecord:
    op: str
    backend: Backend
    input_dtype: np.dtype
    matched_dtype: np.dtype | None  # the registration key that actually fired; None = generic fallback


class KernelRegistry:
    """(op, dtype, backend) -> kernel_fn, with dtype=None meaning "generic kernel for
    this backend, any dtype". dispatch() tries the exact dtype match first, then that
    backend's generic entry, then gives up - two-tier fallback, never a third backend
    silently substituted for the one the caller asked for."""

    def __init__(self):
        self._kernels: dict[tuple[str, np.dtype | None, Backend], callable] = {}
        self.log: list[DispatchRecord] = []

    def register(self, op: str, backend: Backend, dtype: np.dtype | None = None):
        def decorator(fn):
            self._kernels[(op, dtype, backend)] = fn
            return fn
        return decorator

    def dispatch(self, op: str, *args: np.ndarray, backend: Backend) -> np.ndarray:
        input_dtype = np.result_type(*args)
        for candidate in (input_dtype, None):
            fn = self._kernels.get((op, candidate, backend))
            if fn is not None:
                self.log.append(DispatchRecord(op, backend, input_dtype, candidate))
                return fn(*args)
        raise DispatchError(f"no kernel for op={op!r} dtype={input_dtype} backend={backend.value}")


registry = KernelRegistry()


@registry.register("add", Backend.CPU, np.dtype("float32"))
def _add_cpu_f32(a, b):
    # Reference kernel: correct but deliberately unvectorized, standing in for a
    # hand-tuned specialized path that only exists for the hot dtype.
    out = np.empty(a.shape, dtype=np.float32)
    fa, fb, fo = a.reshape(-1), b.reshape(-1), out.reshape(-1)
    for i in range(fa.size):
        fo[i] = fa[i] + fb[i]
    return out


@registry.register("add", Backend.CPU)
def _add_cpu_generic(a, b):
    return a + b


@registry.register("add", Backend.GPU)
def _add_gpu_generic(a, b):
    return a + b


@registry.register("matmul", Backend.CPU, np.dtype("float32"))
def _matmul_cpu_f32(a, b):
    return a.astype(np.float32) @ b.astype(np.float32)


@registry.register("matmul", Backend.GPU)
def _matmul_gpu_generic(a, b):
    return a @ b


@registry.register("relu", Backend.CPU)
def _relu_cpu_generic(a):
    return np.maximum(a, 0)


def main():
    rng = np.random.default_rng(4)
    a32 = rng.uniform(-2, 2, size=(4, 4)).astype(np.float32)
    b32 = rng.uniform(-2, 2, size=(4, 4)).astype(np.float32)
    a_i32 = rng.integers(-5, 5, size=(3, 3)).astype(np.int32)
    b_i32 = rng.integers(-5, 5, size=(3, 3)).astype(np.int32)

    print("dispatch calls and which kernel fired:\n")

    r1 = registry.dispatch("add", a32, b32, backend=Backend.CPU)     # exact float32 CPU kernel
    r2 = registry.dispatch("add", a_i32, b_i32, backend=Backend.CPU)  # falls back to CPU generic
    r3 = registry.dispatch("add", a32, b32, backend=Backend.GPU)     # falls back to GPU generic
    r4 = registry.dispatch("matmul", a32, b32, backend=Backend.CPU)  # exact float32 CPU kernel
    r5 = registry.dispatch("matmul", a_i32, b_i32, backend=Backend.GPU)  # GPU generic, any dtype
    r6 = registry.dispatch("relu", a32, backend=Backend.CPU)         # CPU generic (only relu kernel)

    for rec in registry.log:
        kind = "exact" if rec.matched_dtype is not None else "generic fallback"
        print(f"  {rec.op:<7} dtype={str(rec.input_dtype):<7} backend={rec.backend.value:<3} -> {kind}")

    print("\nresults vs numpy:")
    checks = [
        (r1, a32 + b32, "add f32 CPU (specialized)"),
        (r2, a_i32 + b_i32, "add i32 CPU (generic fallback)"),
        (r3, a32 + b32, "add f32 GPU (generic)"),
        (r4, a32 @ b32, "matmul f32 CPU (specialized)"),
        (r5, a_i32 @ b_i32, "matmul i32 GPU (generic)"),
        (r6, np.maximum(a32, 0), "relu f32 CPU (generic)"),
    ]
    for result, expected, label in checks:
        ok = np.allclose(result, expected)
        print(f"  {label:<32} matches numpy: {ok}")
        assert ok, f"{label} mismatch"

    print("\nrejecting dispatches with no matching kernel at all:")
    for op, args, backend in [("matmul", (a_i32, b_i32), Backend.CPU), ("relu", (a32,), Backend.GPU)]:
        try:
            registry.dispatch(op, *args, backend=backend)
            raise AssertionError(f"expected DispatchError for {op}/{backend.value}")
        except DispatchError as e:
            print(f"  rejected as expected: {e}")

    # Selection logic actually did what the log claims: exact matches used the
    # dtype-specific kernel, fallbacks used the generic (matched_dtype is None).
    exact_calls = [rec for rec in registry.log if rec.matched_dtype is not None]
    fallback_calls = [rec for rec in registry.log if rec.matched_dtype is None]
    assert len(exact_calls) == 2 and all(rec.op in ("add", "matmul") for rec in exact_calls)
    assert len(fallback_calls) == 4

    print(f"\nself-check passed: {len(registry.log)} dispatches all produced numpy-correct "
          f"results ({len(exact_calls)} via specialized kernels, {len(fallback_calls)} via "
          f"generic fallback), and dispatches with no matching kernel raised DispatchError.")


if __name__ == "__main__":
    main()
