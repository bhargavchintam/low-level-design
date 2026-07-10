"""Mini ndarray - shape/strides, broadcasting, elementwise ops and matmul over a flat
Python buffer, verified element-for-element against real numpy on the same inputs.

The point isn't to reimplement numpy; it's the one idea that makes numpy fast and
"transpose is free": an ndarray is a flat 1-D buffer plus a (shape, strides) view over
it. Reshape, transpose and broadcasting never copy or move a single element - they only
change the strides used to walk the same buffer. A real op (add, matmul, sum) is the one
place data actually gets touched.
"""

import numpy as np
from abc import ABC, abstractmethod
from math import prod


class ShapeError(Exception):
    pass


def _broadcast_shape(a: tuple[int, ...], b: tuple[int, ...]) -> tuple[int, ...]:
    # Right-align shorter shape and pad with 1s, then numpy's broadcasting rule:
    # dims match if equal, or either is 1.
    n = max(len(a), len(b))
    a = (1,) * (n - len(a)) + a
    b = (1,) * (n - len(b)) + b
    out = []
    for da, db in zip(a, b):
        if da != db and da != 1 and db != 1:
            raise ShapeError(f"shapes {a} and {b} are not broadcastable")
        out.append(max(da, db))
    return tuple(out)


class Tensor:
    """Flat `data` buffer + `shape` + `strides` (in elements, not bytes - this is a
    teaching model, not a memory-layout-accurate one). `strides[i] == 0` is how a
    broadcast dimension is represented: every index along it reads the same element."""

    def __init__(self, data: list[float], shape: tuple[int, ...], strides: tuple[int, ...] | None = None):
        self.data = data
        self.shape = shape
        self.strides = strides if strides is not None else self._contiguous_strides(shape)

    @staticmethod
    def _contiguous_strides(shape: tuple[int, ...]) -> tuple[int, ...]:
        strides = [1] * len(shape)
        for i in range(len(shape) - 2, -1, -1):
            strides[i] = strides[i + 1] * shape[i + 1]
        return tuple(strides)

    @classmethod
    def from_numpy(cls, arr: np.ndarray) -> "Tensor":
        return cls(arr.astype(float).flatten().tolist(), arr.shape)

    def to_numpy(self) -> np.ndarray:
        out = np.empty(self.shape, dtype=float)
        for idx in np.ndindex(*self.shape) if self.shape else [()]:
            out[idx] = self._get(idx)
        return out

    def _get(self, index: tuple[int, ...]) -> float:
        offset = sum(i * s for i, s in zip(index, self.strides))
        return self.data[offset]

    def reshape(self, shape: tuple[int, ...]) -> "Tensor":
        if prod(shape) != prod(self.shape):
            raise ShapeError(f"cannot reshape {self.shape} ({prod(self.shape)} elems) into {shape} ({prod(shape)} elems)")
        if self.strides != self._contiguous_strides(self.shape):
            raise ShapeError("reshape requires a contiguous tensor (no view support for this case)")
        return Tensor(self.data, shape)

    def transpose(self, axes: tuple[int, ...] | None = None) -> "Tensor":
        axes = axes or tuple(reversed(range(len(self.shape))))
        new_shape = tuple(self.shape[a] for a in axes)
        new_strides = tuple(self.strides[a] for a in axes)
        return Tensor(self.data, new_shape, new_strides)

    def broadcast_to(self, shape: tuple[int, ...]) -> "Tensor":
        padded_strides = (0,) * (len(shape) - len(self.shape)) + self.strides
        padded_shape = (1,) * (len(shape) - len(self.shape)) + self.shape
        new_strides = []
        for old_dim, old_stride, new_dim in zip(padded_shape, padded_strides, shape):
            if old_dim == new_dim:
                new_strides.append(old_stride)
            elif old_dim == 1:
                new_strides.append(0)  # broadcast dim: stride 0 means "always read index 0"
            else:
                raise ShapeError(f"cannot broadcast {self.shape} to {shape}")
        return Tensor(self.data, shape, tuple(new_strides))

    def __repr__(self):
        return f"Tensor(shape={self.shape}, strides={self.strides})"


class Op(ABC):
    """Strategy for a binary elementwise op: only the scalar combine rule differs
    between add/mul/etc, so BinaryElementwiseOp handles broadcasting once and every
    concrete op just plugs in `combine`."""

    @abstractmethod
    def combine(self, a: float, b: float) -> float:
        ...


class Add(Op):
    def combine(self, a, b):
        return a + b


class Mul(Op):
    def combine(self, a, b):
        return a * b


class BinaryElementwiseOp:
    def __init__(self, op: Op):
        self.op = op

    def __call__(self, x: Tensor, y: Tensor) -> Tensor:
        out_shape = _broadcast_shape(x.shape, y.shape)
        xb, yb = x.broadcast_to(out_shape), y.broadcast_to(out_shape)
        out = [0.0] * prod(out_shape)
        strides = Tensor._contiguous_strides(out_shape)
        for idx in np.ndindex(*out_shape) if out_shape else [()]:
            offset = sum(i * s for i, s in zip(idx, strides))
            out[offset] = self.op.combine(xb._get(idx), yb._get(idx))
        return Tensor(out, out_shape)


add = BinaryElementwiseOp(Add())
mul = BinaryElementwiseOp(Mul())


def matmul(x: Tensor, y: Tensor) -> Tensor:
    """2-D matmul only, walked via strides so a transposed operand (stride-swapped,
    not physically transposed) multiplies correctly with zero extra copies."""
    if len(x.shape) != 2 or len(y.shape) != 2:
        raise ShapeError("matmul here only supports 2-D tensors")
    m, k = x.shape
    k2, n = y.shape
    if k != k2:
        raise ShapeError(f"inner dimensions must match: {x.shape} @ {y.shape}")

    out = [0.0] * (m * n)
    for i in range(m):
        for j in range(n):
            out[i * n + j] = sum(x._get((i, p)) * y._get((p, j)) for p in range(k))
    return Tensor(out, (m, n))


def assert_close(t: Tensor, expected: np.ndarray, label: str, atol: float = 1e-9):
    actual = t.to_numpy()
    if not np.allclose(actual, expected, atol=atol):
        raise AssertionError(f"{label}: mismatch\nours:\n{actual}\nnumpy:\n{expected}")
    print(f"  {label:<28} shape={t.shape}  matches numpy (max abs diff={np.max(np.abs(actual - expected)):.2e})")


def main():
    rng = np.random.default_rng(5)
    a_np = rng.uniform(-3, 3, size=(2, 3))
    b_np = rng.uniform(-3, 3, size=(3,))       # broadcasts against a row of a
    c_np = rng.uniform(-3, 3, size=(3, 4))

    a, b, c = Tensor.from_numpy(a_np), Tensor.from_numpy(b_np), Tensor.from_numpy(c_np)

    print("elementwise ops vs numpy:")
    assert_close(add(a, b), a_np + b_np, "add (2,3) + (3,) broadcast")
    assert_close(mul(a, b), a_np * b_np, "mul (2,3) * (3,) broadcast")

    print("\nreshape / transpose (view-only, no data copy) vs numpy:")
    assert_close(a.reshape((3, 2)), a_np.reshape(3, 2), "reshape (2,3) -> (3,2)")
    assert_close(a.transpose(), a_np.T, "transpose (2,3) -> (3,2)")

    print("\nmatmul (including a transposed operand) vs numpy:")
    assert_close(matmul(a, c), a_np @ c_np, "matmul (2,3) @ (3,4)")
    d_np = rng.uniform(-3, 3, size=(4, 3))
    d = Tensor.from_numpy(d_np)
    assert_close(matmul(a, d.transpose()), a_np @ d_np.T, "matmul (2,3) @ (4,3).T")

    print("\nbroadcasting a scalar-like (1,1) tensor against (2,3):")
    scalar = Tensor.from_numpy(np.array([[2.0]]))
    assert_close(mul(a, scalar), a_np * 2.0, "mul (2,3) * (1,1) broadcast")

    print("\nrejecting an illegal broadcast (2,3) vs (4,):")
    bad = Tensor.from_numpy(rng.uniform(size=(4,)))
    try:
        add(a, bad)
        raise AssertionError("expected ShapeError for incompatible shapes")
    except ShapeError as e:
        print(f"  rejected as expected: {e}")

    # Prove transpose really is a zero-copy view: same underlying buffer, different strides.
    t = a.transpose()
    assert t.data is a.data and t.strides != a.strides
    print("\nself-check passed: every op matched numpy element-for-element, "
          "and transpose reused the same buffer (true view, no copy).")


if __name__ == "__main__":
    main()
