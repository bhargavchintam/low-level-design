# Data Loader

## Problem
Build a PyTorch-style `Dataset` + `DataLoader` pair: a `Dataset` exposes
indexed samples, and a `DataLoader` iterates it in batches, optionally
shuffling each epoch, applying per-sample transforms, and dropping a trailing
partial batch on request.

## Design
- `Dataset` (ABC) - `__len__` and `__getitem__(index)`, the whole contract
  `DataLoader` needs. It knows nothing about batching or shuffling.
- `Compose` - chains a list of transform callables into one; each transform
  (`Normalize`, `AddGaussianNoise`) is just `__call__(x) -> x`.
- `ArrayDataset` - wraps feature/label numpy arrays and owns an optional
  transform, applied in `__getitem__` (matches torchvision's convention:
  the dataset applies its own transform, `DataLoader` stays agnostic to it).
- `DataLoader.__iter__` - builds an index permutation (shuffled fresh every
  epoch if `shuffle=True`), slices it into `batch_size` chunks, fetches each
  sample via `dataset[i]`, and hands the batch to `collate_fn` (default:
  stack into numpy arrays). `drop_last` discards a trailing undersized batch.

## Patterns used
- **Iterator** - `DataLoader.__iter__` is a generator; each `for batch in
  loader` re-invokes it, which is also what makes the "reshuffle every
  epoch" behavior fall out naturally rather than needing an explicit
  `reset()`.
- **Decorator/Composite** - `Compose` wraps transforms around each other
  without either the transforms or `Dataset` knowing how many are chained.

## How to run
```
cd /Users/bhargav/Desktop/low-level-design/data-loader
python3 main.py
```
The demo runs two epochs over a 23-sample dataset with `batch_size=5,
shuffle=True`, verifying every epoch is a full permutation of the dataset
(no sample skipped or repeated), then runs a `drop_last=True` pass and
verifies every yielded batch is full-sized.
