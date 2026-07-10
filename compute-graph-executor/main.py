"""Compute graph executor - build an op DAG, execute it in topological order, and cache
each node's output so a node with fan-out > 1 is computed exactly once no matter how many
downstream nodes depend on it. Same reason TF/autodiff graphs memoize forward values
instead of recomputing a shared subexpression once per consumer.
"""

import numpy as np
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


class GraphError(Exception):
    pass


class Op(ABC):
    """A node's compute rule: how its inputs' values turn into this node's value.
    Every concrete Op just plugs in the math; the executor doesn't know or care."""

    @abstractmethod
    def compute(self, *inputs: np.ndarray) -> np.ndarray:
        ...


class Const(Op):
    def __init__(self, value):
        self.value = np.asarray(value, dtype=float)

    def compute(self) -> np.ndarray:
        return self.value


class Add(Op):
    def compute(self, a, b):
        return a + b


class Mul(Op):
    def compute(self, a, b):
        return a * b


class MatMul(Op):
    def compute(self, a, b):
        return a @ b


class Relu(Op):
    def compute(self, a):
        return np.maximum(a, 0.0)


@dataclass
class Node:
    name: str
    op: Op
    inputs: list[str] = field(default_factory=list)


class Graph:
    """Just the DAG structure - nodes and their declared dependencies. No execution
    logic here, so the same graph can be run by different executors/policies."""

    def __init__(self):
        self.nodes: dict[str, Node] = {}

    def add(self, name: str, op: Op, inputs: list[str] | None = None) -> str:
        if name in self.nodes:
            raise GraphError(f"node {name!r} already exists")
        for dep in inputs or []:
            if dep not in self.nodes:
                raise GraphError(f"unknown dependency {dep!r} for node {name!r}")
        self.nodes[name] = Node(name, op, inputs or [])
        return name

    def ancestor_order(self, target: str) -> list[str]:
        """DFS post-order over `target`'s ancestor subgraph = a valid topological
        order restricted to just the nodes `target` actually depends on, so unrelated
        branches of a larger graph are never touched."""
        if target not in self.nodes:
            raise GraphError(f"unknown node {target!r}")
        visited: set[str] = set()
        order: list[str] = []

        def visit(name: str):
            if name in visited:
                return
            visited.add(name)
            for dep in self.nodes[name].inputs:
                visit(dep)
            order.append(name)

        visit(target)
        return order


class Executor:
    """Runs a Graph's nodes in dependency order into a value cache keyed by node
    name. Passing the same cache dict across multiple run() calls is what makes
    shared ancestors compute once total instead of once per target - the cache
    persists, `eval_count` records how many times each node's op actually fired."""

    def __init__(self, graph: Graph):
        self.graph = graph
        self.eval_count: dict[str, int] = {}

    def run(self, target: str, cache: dict[str, np.ndarray]) -> np.ndarray:
        for name in self.graph.ancestor_order(target):
            if name in cache:
                continue
            node = self.graph.nodes[name]
            args = [cache[dep] for dep in node.inputs]
            cache[name] = node.op.compute(*args)
            self.eval_count[name] = self.eval_count.get(name, 0) + 1
        return cache[target]


def main():
    rng = np.random.default_rng(11)
    x_val = rng.uniform(-1, 1, size=(4, 3))
    w_val = rng.uniform(-1, 1, size=(3, 2))
    b_val = rng.uniform(-1, 1, size=(2,))

    g = Graph()
    g.add("x", Const(x_val))
    g.add("w", Const(w_val))
    g.add("b", Const(b_val))
    g.add("h", MatMul(), ["x", "w"])          # x @ w
    g.add("pre_act", Add(), ["h", "b"])       # x @ w + b  -- shared by both branches below
    g.add("relu_out", Relu(), ["pre_act"])    # branch 1: relu(x @ w + b)
    g.add("scaled", Const(2.0))
    g.add("scaled_out", Mul(), ["pre_act", "scaled"])  # branch 2: 2 * (x @ w + b)

    executor = Executor(g)
    cache: dict[str, np.ndarray] = {}

    relu_out = executor.run("relu_out", cache)
    scaled_out = executor.run("scaled_out", cache)   # shares "pre_act" with the run above

    print("graph: x, w, b -> h = x@w -> pre_act = h+b -> {relu_out = relu(pre_act), scaled_out = 2*pre_act}")
    print(f"\neval counts (should be 1 per node - pre_act feeds two targets but only ran once):")
    for name in ["x", "w", "b", "h", "pre_act", "relu_out", "scaled", "scaled_out"]:
        print(f"  {name:<12} evaluated {executor.eval_count[name]}x")

    expected_pre_act = x_val @ w_val + b_val
    expected_relu = np.maximum(expected_pre_act, 0.0)
    expected_scaled = expected_pre_act * 2.0

    print("\nresult vs hand-computed numpy expression:")
    print(f"  relu_out   max abs diff = {np.max(np.abs(relu_out - expected_relu)):.2e}")
    print(f"  scaled_out max abs diff = {np.max(np.abs(scaled_out - expected_scaled)):.2e}")

    assert np.allclose(relu_out, expected_relu)
    assert np.allclose(scaled_out, expected_scaled)
    assert all(count == 1 for count in executor.eval_count.values()), "a node was recomputed - caching failed"
    assert executor.eval_count["pre_act"] == 1, "shared ancestor pre_act should only compute once across both targets"

    # A fresh, unshared cache must reproduce identical results - caching changes
    # *how many times* work happens, never *what* the answer is.
    fresh_cache: dict[str, np.ndarray] = {}
    fresh_relu = executor.run("relu_out", fresh_cache)
    assert np.array_equal(fresh_relu, relu_out)

    print("\nself-check passed: outputs match numpy exactly, and every node "
          "(including the shared branch point) evaluated exactly once.")


if __name__ == "__main__":
    main()
