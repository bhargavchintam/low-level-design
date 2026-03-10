# Vector Store

## Problem
Build an in-memory vector store: add embeddings with IDs and metadata, and
run top-k nearest-neighbor search under a chosen distance metric. Support
both an exact brute-force search and a faster approximate index, and verify
the approximate index's results against brute force.

## Design
- `SimilarityMetric` (ABC) - `score(query, vectors) -> scores`, always
  "higher is better" so every index can `argsort` descending regardless of
  which metric is plugged in. `CosineSimilarity` scores directly;
  `L2Distance` returns *negative* distance so the same convention holds.
- `VectorIndex` (ABC) - `add(ids, vectors)`, `search(query, k)`.
  - `BruteForceIndex` - scores every stored vector against the query,
    O(n·d) per search. This is the correctness ground truth.
  - `IVFIndex` - k-means partitions vectors into `nlist` clusters at build
    time (lazy, on first search); a search only scans the `nprobe` clusters
    whose centroid is nearest the query instead of every vector - the same
    scan-fewer-candidates trade-off real IVF indexes (e.g. Faiss) make.
- `VectorStore` - user-facing wrapper: owns `id -> metadata` and delegates
  the actual nearest-neighbor math to whichever `VectorIndex` it's given.
- `recall_at_k` - fraction of a candidate index's top-k IDs that also appear
  in brute force's top-k, the standard way to measure an ANN index's
  accuracy against ground truth (an approximate index isn't expected to
  match exactly, unlike two implementations of the same exact algorithm).

## Patterns used
- **Strategy**, twice over - `SimilarityMetric` picks *how* two vectors are
  compared; `VectorIndex` picks *which* candidates get compared at all.
  `VectorStore` composes one of each without knowing their internals.

## How to run
```
cd /Users/bhargav/Desktop/low-level-design/vector-store
python3 main.py
```
The demo builds a 200-vector, 10-cluster dataset with deliberately
overlapping (noisy) clusters, runs the same top-5 queries against
`BruteForceIndex` and `IVFIndex`, and asserts `IVFIndex`'s average recall@5
clears a 0.70 threshold (typically ~0.77-0.85) - high enough to be useful,
low enough to show the trade-off is real rather than trivially perfect.
