# Experiment Tracker

## Problem
Build an MLflow-style experiment tracker: start a run, log hyperparameters
and time-series metrics against it, and later compare runs by a metric or
pull out the best one. A run must always end up marked finished or failed,
even if the code inside it raises.

## Design
- `Run` - holds `params` (a flat dict) and `metrics` (`dict[str, list[MetricPoint]]`,
  one time series per metric name). `log_metric` auto-increments `step` if the
  caller doesn't supply one, so simple loops don't need to track their own
  step counter.
- `RunContext` - a context manager wrapping a `Run`; `__exit__` sets
  `status` to `FINISHED` or `FAILED` depending on whether an exception
  propagated, and always records `end_time`. Mirrors
  `with mlflow.start_run() as run: ...`.
- `ExperimentTracker` - `start_run` (returns a `RunContext`), `get_run`,
  `list_runs`, `compare_runs(metric_key)` (every run's latest value for that
  metric, ranked descending), `best_run(metric_key, mode)` (the run whose
  best-ever value for that metric is the overall max/min).

## Patterns used
- **Context manager** - `RunContext` guarantees a run's lifecycle is closed
  out correctly regardless of how the `with` block exits, the same job
  `contextlib`-style resource managers do for files or locks.

## How to run
```
cd /Users/bhargav/Desktop/low-level-design/experiment-tracker
python3 main.py
```
The demo runs a small learning-rate sweep (4 runs, simulated training),
then calls `compare_runs("accuracy")` and `best_run("accuracy", mode="max")`,
asserting the reported best run's value matches the true global max across
every run's every logged point.
