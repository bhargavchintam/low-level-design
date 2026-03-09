# Kernel Dispatcher

## Problem
Design the dispatch layer sitting under a tensor op call: `add`, `matmul`, etc.
each have several concrete implementations depending on dtype and target
backend (a hand-tuned specialized kernel for the hot dtype, a slower generic
kernel for everything else), and calling the op should route to the right one
without an if/elif chain baked into every op.

## Design
- `Backend` (Enum) - `CPU`, `GPU` (the GPU path is a vectorized numpy
  function standing in for a real device kernel).
- `KernelRegistry` - `_kernels: dict[(op, dtype | None, backend) -> fn]`.
  `register` is a decorator that inserts into this table; `dispatch` computes
  the call's actual dtype via `np.result_type`, tries the exact `(op, dtype,
  backend)` key first, then falls back to `(op, None, backend)` - that
  backend's generic, any-dtype kernel - and raises `DispatchError` if neither
  exists. Every successful dispatch is logged as a `DispatchRecord`
  (`matched_dtype=None` means the call went through the generic fallback, not
  the specialized path).
- Kernels registered: a deliberately unvectorized reference `add` kernel for
  `float32` on CPU (the "specialized, hand-tuned" slot), generic `add` for
  CPU and GPU, a specialized `matmul` for `float32` on CPU, generic `matmul`
  for GPU, and only a generic `relu` on CPU - so some dispatches must fall
  back and some combinations (`matmul` int32 on CPU, `relu` on GPU) have no
  kernel at all and must raise.

## Patterns used
- **Strategy + Registry** - each kernel function is a strategy; the registry
  is the lookup table deciding which strategy runs for a given call, decoupled
  from both the op call site and the kernel implementations themselves.

## How to run
```
cd /Users/bhargav/Desktop/low-level-design/kernel-dispatcher
python3 main.py
```
