"""Mini autograd - reverse-mode automatic differentiation over a scalar computation graph.

Each Value node is a Composite: it holds its own data/grad plus references to the
child nodes that produced it and a closure knowing how to route its incoming
gradient to those children (the local derivative, chain-rule style). backward()
topologically sorts the graph and applies those closures in reverse build order.
"""

import math
import random


class Value:
    def __init__(self, data: float, children: tuple["Value", ...] = (), op: str = ""):
        self.data = data
        self.grad = 0.0
        self._children = children
        self._op = op
        self._backward = lambda: None  # default: leaf node, nothing to propagate

    def __add__(self, other):
        other = other if isinstance(other, Value) else Value(other)
        out = Value(self.data + other.data, (self, other), "+")

        def _backward():
            self.grad += out.grad
            other.grad += out.grad
        out._backward = _backward
        return out

    def __mul__(self, other):
        other = other if isinstance(other, Value) else Value(other)
        out = Value(self.data * other.data, (self, other), "*")

        def _backward():
            self.grad += other.data * out.grad
            other.grad += self.data * out.grad
        out._backward = _backward
        return out

    def __pow__(self, exponent: float):
        assert isinstance(exponent, (int, float))
        out = Value(self.data ** exponent, (self,), f"**{exponent}")

        def _backward():
            self.grad += exponent * (self.data ** (exponent - 1)) * out.grad
        out._backward = _backward
        return out

    def relu(self):
        out = Value(max(0.0, self.data), (self,), "relu")

        def _backward():
            self.grad += (out.data > 0) * out.grad
        out._backward = _backward
        return out

    def tanh(self):
        t = math.tanh(self.data)
        out = Value(t, (self,), "tanh")

        def _backward():
            self.grad += (1 - t * t) * out.grad
        out._backward = _backward
        return out

    def __neg__(self):
        return self * -1

    def __sub__(self, other):
        return self + (-other if isinstance(other, Value) else Value(-other))

    def __radd__(self, other):
        return self + other

    def __rmul__(self, other):
        return self * other

    def __truediv__(self, other):
        other = other if isinstance(other, Value) else Value(other)
        return self * other ** -1

    def backward(self):
        order: list[Value] = []
        visited: set[int] = set()

        def topo(node: "Value"):
            if id(node) in visited:
                return
            visited.add(id(node))
            for child in node._children:
                topo(child)
            order.append(node)
        topo(self)

        self.grad = 1.0  # d(self)/d(self) = 1, the seed for the chain rule
        for node in reversed(order):
            node._backward()

    def __repr__(self):
        return f"Value(data={self.data:.4f}, grad={self.grad:.4f})"


def numerical_gradient(f, inputs: list[Value], eps: float = 1e-6) -> list[float]:
    """Central-difference gradient check, independent of the autograd machinery above."""
    grads = []
    for i in range(len(inputs)):
        original = inputs[i].data

        inputs[i].data = original + eps
        plus = f(inputs).data

        inputs[i].data = original - eps
        minus = f(inputs).data

        inputs[i].data = original
        grads.append((plus - minus) / (2 * eps))
    return grads


def expression(inputs: list[Value]) -> Value:
    """f(x, y, z) = relu(x*y + z) * tanh(x) - z**2, an arbitrary small graph
    that touches every op the autograd supports."""
    x, y, z = inputs
    return (x * y + z).relu() * x.tanh() - z ** 2


def main():
    random.seed(0)
    x, y, z = Value(0.6), Value(-1.3), Value(0.9)

    out = expression([x, y, z])
    out.backward()

    print(f"expression value: {out.data:.6f}")
    print(f"analytic grads -> dx={x.grad:.6f}  dy={y.grad:.6f}  dz={z.grad:.6f}")

    fresh = [Value(x.data), Value(y.data), Value(z.data)]
    numeric = numerical_gradient(expression, fresh)
    print(f"numeric  grads -> dx={numeric[0]:.6f}  dy={numeric[1]:.6f}  dz={numeric[2]:.6f}")

    analytic = [x.grad, y.grad, z.grad]
    max_diff = max(abs(a - n) for a, n in zip(analytic, numeric))
    print(f"\nmax |analytic - numeric| = {max_diff:.8f}")
    assert max_diff < 1e-4, "backward() disagrees with the numerical gradient"
    print("self-check passed: backward() matches finite-difference gradients.")

    # A second, larger random graph as a sanity net beyond the one hand-picked case.
    print("\nrandom trials:")
    worst = 0.0
    for trial in range(5):
        vals = [Value(random.uniform(-2, 2)) for _ in range(3)]
        expression(vals).backward()
        num = numerical_gradient(expression, [Value(v.data) for v in vals])
        diff = max(abs(v.grad - n) for v, n in zip(vals, num))
        worst = max(worst, diff)
        print(f"  trial {trial}: inputs={[round(v.data, 3) for v in vals]}  max_diff={diff:.8f}")
    assert worst < 1e-4
    print(f"self-check passed: worst-case diff across trials = {worst:.8f}")


if __name__ == "__main__":
    main()
