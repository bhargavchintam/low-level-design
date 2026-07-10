# Tensor NDArray

## Problem
Design a minimal ndarray: a flat buffer plus shape/strides metadata, supporting
reshape, transpose, broadcasting, elementwise ops and 2-D matmul - and prove it's
correct by checking every result element-for-element against real numpy on the
same random inputs.

## Design
- `Tensor` - a flat `data` list plus `shape` and `strides` (in elements). The
  core idea numpy is built on: `reshape`/`transpose`/`broadcast_to` never touch
  `data`, they only compute new strides over the *same* buffer. A stride of `0`
  along a dimension is how broadcasting is represented - every index along
  that axis reads the same underlying element.
- `_broadcast_shape` - numpy's broadcasting rule (right-align, pad with 1s,
  dims must match or one must be 1), used to compute the output shape before
  any op runs.
- `Op` (ABC) - `combine(a, b) -> float`, the one thing that differs between
  `Add` and `Mul`. `BinaryElementwiseOp` does the broadcasting and index
  walking once and calls `op.combine` per output element - adding a new
  elementwise op means writing a two-line `Op` subclass, not touching the
  broadcasting logic.
- `matmul` - 2-D only, walked entirely through `Tensor._get` (which reads via
  strides), so multiplying by a transposed operand needs zero extra copies -
  transpose already just swapped the strides.
- `assert_close` - converts a `Tensor` to a real numpy array and diffs it
  against the numpy-computed expected result with `np.allclose`.

## Patterns used
- **Strategy** - `Op` is the swappable per-element combine rule;
  `BinaryElementwiseOp` is the shape-handling logic that stays fixed while
  `Op` implementations vary.

## How to run
```
cd /Users/bhargav/Desktop/low-level-design/tensor-ndarray
python3 main.py
```
