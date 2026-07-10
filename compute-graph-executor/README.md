# Compute Graph Executor

## Problem
Design the execution core of something like a TF graph or an autodiff engine's
forward pass: nodes are ops with declared dependencies, edges are data flow,
and running a target node must execute every ancestor exactly once - even when
several nodes downstream share an ancestor - not once per consumer.

## Design
- `Op` (ABC) - `compute(*inputs) -> ndarray`. `Const`, `Add`, `Mul`, `MatMul`,
  `Relu` each implement one op; the executor never branches on which op it's
  running.
- `Node` / `Graph` - a `Node` is an op plus the names of the nodes it depends
  on; `Graph` is just the DAG (`add`, and `ancestor_order`, a DFS post-order
  over a target's ancestor subgraph - a topological order restricted to only
  the nodes that actually feed the target, so unrelated branches of a larger
  graph are never touched).
- `Executor` - walks `ancestor_order(target)` and fills a `cache: dict[name ->
  value]` skipping any node already present. Passing the *same* cache dict
  across multiple `run()` calls is what makes a shared ancestor compute once
  total instead of once per target; `eval_count` records how many times each
  node's `compute` actually fired, which is what the demo asserts on.
- Demo graph: `pre_act = x @ w + b` feeds two branches, `relu(pre_act)` and
  `2 * pre_act`. Both targets are run into one shared cache, so `pre_act` (and
  everything below it) must show `eval_count == 1` even though two nodes
  depend on it.

## Patterns used
- **Strategy** - `Op` is the swappable per-node compute rule.
- Memoization / caching - the executor's cache is what turns "DAG" into
  "compute each shared subexpression once," the standard reason real
  computation graphs cache forward values at all.

## How to run
```
cd /Users/bhargav/Desktop/low-level-design/compute-graph-executor
python3 main.py
```
