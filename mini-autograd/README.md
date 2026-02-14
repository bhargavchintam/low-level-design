# Mini Autograd

## Problem
Build reverse-mode automatic differentiation over a scalar computation graph:
a `Value` type that supports `+`, `*`, `**`, `relu`, `tanh`, records how each
result was produced, and can compute the gradient of any output with respect
to every input that fed into it via a single `backward()` call.

## Design
- `Value` - a Composite: each node holds its own `data`/`grad`, a tuple of the
  child nodes that produced it, and a `_backward` closure that knows the local
  derivative for that specific op and how to route the incoming gradient to
  its children (the chain rule, one node at a time).
- Each operator (`__add__`, `__mul__`, `__pow__`, `relu`, `tanh`, ...)
  constructs a new `Value` referencing its inputs as children and attaches
  the matching `_backward` closure - the graph is built implicitly just by
  writing normal Python arithmetic.
- `Value.backward()` - topologically sorts the graph (children before
  parents), seeds the root's gradient at 1.0, then walks the sort in reverse
  calling each node's `_backward`, accumulating gradients into `.grad`.
- `numerical_gradient` - an independent central-difference gradient estimate
  that never touches the autograd machinery, used purely to verify
  `backward()` is correct.

## Patterns used
- **Composite** - `Value` nodes form a tree (DAG) of the same type; operations
  on the whole graph (`backward`) are implemented by having each node handle
  its own local piece and letting the recursion (topological walk) handle
  the aggregation.

## How to run
```
cd /Users/bhargav/Desktop/low-level-design/mini-autograd
python3 main.py
```
The demo builds an expression touching every supported op, runs `backward()`,
then cross-checks every gradient against finite differences (analytic and
numeric agree to `<1e-4` across the hand-picked case and five random trials).
