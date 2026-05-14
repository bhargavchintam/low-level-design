# Model Registry

## Problem
Design an MLflow-style model registry: register named models, create immutable
versions under each name, and move a version through lifecycle stages
(`None -> Staging -> Production -> Archived`). Only one version per model should
ever be in `Production` at a time, and illegal stage jumps should be rejected
rather than silently applied.

## Design
- `Stage` (Enum) - `NONE`, `STAGING`, `PRODUCTION`, `ARCHIVED`.
- `_ALLOWED_TRANSITIONS` - a table mapping each stage to the set of stages it can
  legally move to. This is the state machine; `ModelRegistry.transition_stage`
  just looks the move up instead of encoding rules as if/elif branches.
- `ModelVersion` - immutable-ish record: name, version number, source path,
  metrics, current stage, creation time.
- `RegisteredModel` - all versions registered under one model name, auto-assigns
  the next version number.
- `ModelRegistry` - `register_model`, `create_version`, `transition_stage`,
  `get_by_stage`, `latest_version`. Promoting a version to `Production`
  auto-archives whatever version was previously `Production` for that model,
  so the "exactly one Production version" invariant never has to be checked
  by callers.

## Patterns used
- **State** - `Stage` plus the `_ALLOWED_TRANSITIONS` table encode a state
  machine as data; `transition_stage` is a generic state-machine executor that
  doesn't need to change when the transition rules do.

## How to run
```
cd /Users/bhargav/Desktop/low-level-design/model-registry
python3 main.py
```
