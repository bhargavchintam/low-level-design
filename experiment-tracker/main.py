"""Experiment tracker demo - MLflow-style start_run/log_param/log_metric, run comparison.

RunContext is a context manager (mirrors `with mlflow.start_run() as run:`) so a run is
always marked FINISHED or FAILED on exit, even if the training loop inside raises.
"""

import math
import random
import time
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class MetricPoint:
    step: int
    value: float
    timestamp: float


class Run:
    def __init__(self, run_id: str, name: str):
        self.run_id = run_id
        self.name = name
        self.params: dict[str, object] = {}
        self.metrics: dict[str, list[MetricPoint]] = defaultdict(list)
        self.status = "RUNNING"
        self.start_time = time.time()
        self.end_time: float | None = None

    def log_param(self, key: str, value):
        self.params[key] = value

    def log_metric(self, key: str, value: float, step: int | None = None):
        if step is None:
            step = len(self.metrics[key])
        self.metrics[key].append(MetricPoint(step, value, time.time()))

    def latest(self, key: str) -> float | None:
        points = self.metrics.get(key)
        return points[-1].value if points else None

    def best(self, key: str, mode: str = "max") -> float | None:
        points = self.metrics.get(key)
        if not points:
            return None
        values = [p.value for p in points]
        return max(values) if mode == "max" else min(values)

    def __repr__(self):
        return f"Run({self.run_id}, {self.name}, status={self.status})"


class RunContext:
    def __init__(self, run: Run):
        self.run = run

    def __enter__(self) -> Run:
        return self.run

    def __exit__(self, exc_type, exc, tb):
        self.run.status = "FAILED" if exc_type else "FINISHED"
        self.run.end_time = time.time()
        return False  # propagate any exception, don't swallow it


class ExperimentTracker:
    def __init__(self, experiment_name: str):
        self.experiment_name = experiment_name
        self._runs: dict[str, Run] = {}
        self._counter = 0

    def start_run(self, name: str | None = None) -> RunContext:
        self._counter += 1
        run_id = f"run-{self._counter:03d}"
        run = Run(run_id, name or run_id)
        self._runs[run_id] = run
        return RunContext(run)

    def get_run(self, run_id: str) -> Run:
        return self._runs[run_id]

    def list_runs(self) -> list[Run]:
        return list(self._runs.values())

    def compare_runs(self, metric_key: str) -> list[tuple[str, str, float]]:
        rows = [(r.run_id, r.name, r.latest(metric_key)) for r in self._runs.values()
                if r.latest(metric_key) is not None]
        return sorted(rows, key=lambda row: row[2], reverse=True)

    def best_run(self, metric_key: str, mode: str = "max") -> Run | None:
        candidates = [(r, r.best(metric_key, mode)) for r in self._runs.values() if r.metrics.get(metric_key)]
        if not candidates:
            return None
        pick = max if mode == "max" else min
        return pick(candidates, key=lambda pair: pair[1])[0]


def train_simulated_model(run: Run, lr: float, hidden_size: int, epochs: int, seed: int):
    """Fake training loop standing in for a real one - deterministic per-seed so the demo
    is reproducible, but shaped so different lr values genuinely converge differently."""
    rng = random.Random(seed)
    run.log_param("lr", lr)
    run.log_param("hidden_size", hidden_size)
    run.log_param("epochs", epochs)

    loss = 2.0
    for epoch in range(epochs):
        decay = math.exp(-lr * (epoch + 1))
        loss = 0.1 + 1.9 * decay + rng.uniform(-0.02, 0.02)
        accuracy = min(0.99, 1.0 - loss / 2.0 + rng.uniform(-0.01, 0.01))
        run.log_metric("loss", round(loss, 4), step=epoch)
        run.log_metric("accuracy", round(accuracy, 4), step=epoch)


def main():
    tracker = ExperimentTracker("lr-sweep")
    configs = [
        {"lr": 0.05, "hidden_size": 32, "seed": 1},
        {"lr": 0.20, "hidden_size": 32, "seed": 2},
        {"lr": 0.50, "hidden_size": 64, "seed": 3},
        {"lr": 0.90, "hidden_size": 64, "seed": 4},  # too aggressive, expect worse accuracy
    ]

    for cfg in configs:
        with tracker.start_run(name=f"lr={cfg['lr']}") as run:
            train_simulated_model(run, lr=cfg["lr"], hidden_size=cfg["hidden_size"], epochs=6, seed=cfg["seed"])

    print("run summaries:")
    for run in tracker.list_runs():
        print(f"  {run.run_id} {run.name:<12} status={run.status}  "
              f"params={run.params}  final_loss={run.latest('loss')}  final_acc={run.latest('accuracy')}")

    print("\ncompare_runs('accuracy'), ranked best to worst:")
    for run_id, name, acc in tracker.compare_runs("accuracy"):
        print(f"  {run_id} {name:<12} accuracy={acc}")

    best = tracker.best_run("accuracy", mode="max")
    print(f"\nbest_run('accuracy', mode=max) -> {best.run_id} ({best.name}), "
          f"best accuracy={best.best('accuracy', 'max')}")

    # self-check: best_run's best value must equal the max across every run's every point
    all_points = [p.value for r in tracker.list_runs() for p in r.metrics["accuracy"]]
    assert best.best("accuracy", "max") == max(all_points)
    assert tracker.compare_runs("accuracy")[0][0] == best.run_id
    print("\nself-check passed: best_run matches the global max, compare_runs ranks it first.")


if __name__ == "__main__":
    main()
