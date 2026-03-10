"""In-memory vector store - Strategy pattern twice over: SimilarityMetric picks how two
vectors are compared, VectorIndex picks how candidates are found before comparing.
BruteForceIndex is the ground truth; IVFIndex trades a little recall for scanning far
fewer vectors, which is exactly the trade-off real ANN indexes (Faiss IVF, etc.) make.
"""

import numpy as np
from abc import ABC, abstractmethod


class SimilarityMetric(ABC):
    """score() must return higher = more similar, so every index can just argsort descending
    regardless of which metric is plugged in."""

    @abstractmethod
    def score(self, query: np.ndarray, vectors: np.ndarray) -> np.ndarray:
        ...


class CosineSimilarity(SimilarityMetric):
    def score(self, query, vectors):
        q = query / (np.linalg.norm(query) + 1e-12)
        v = vectors / (np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-12)
        return v @ q


class L2Distance(SimilarityMetric):
    def score(self, query, vectors):
        return -np.linalg.norm(vectors - query, axis=1)  # negated: closer = higher score


class VectorIndex(ABC):
    @abstractmethod
    def add(self, ids: list[str], vectors: np.ndarray):
        ...

    @abstractmethod
    def search(self, query: np.ndarray, k: int) -> list[tuple[str, float]]:
        ...


class BruteForceIndex(VectorIndex):
    """Scores every stored vector against the query. O(n*d) per search - the correctness
    baseline everything else is measured against."""

    def __init__(self, metric: SimilarityMetric):
        self.metric = metric
        self.ids: list[str] = []
        self.vectors: np.ndarray | None = None

    def add(self, ids: list[str], vectors: np.ndarray):
        self.ids.extend(ids)
        self.vectors = vectors if self.vectors is None else np.vstack([self.vectors, vectors])

    def search(self, query: np.ndarray, k: int) -> list[tuple[str, float]]:
        scores = self.metric.score(query, self.vectors)
        top = np.argsort(-scores)[:k]
        return [(self.ids[i], float(scores[i])) for i in top]


def _kmeans(vectors: np.ndarray, k: int, iters: int, seed: int):
    rng = np.random.default_rng(seed)
    centroids = vectors[rng.choice(len(vectors), size=k, replace=False)].copy()
    assignments = np.zeros(len(vectors), dtype=int)
    for _ in range(iters):
        dists = ((vectors[:, None, :] - centroids[None, :, :]) ** 2).sum(axis=2)
        assignments = dists.argmin(axis=1)
        for c in range(k):
            members = vectors[assignments == c]
            if len(members):
                centroids[c] = members.mean(axis=0)
    return centroids, assignments


class IVFIndex(VectorIndex):
    """Inverted-file index: k-means partitions vectors into `nlist` clusters at build time;
    a search only scans the `nprobe` clusters whose centroid is nearest the query instead of
    every vector. Index is built lazily on first search so add() can be called freely first."""

    def __init__(self, metric: SimilarityMetric, nlist: int = 8, nprobe: int = 2, seed: int = 0):
        self.metric = metric
        self.nlist = nlist
        self.nprobe = nprobe
        self.seed = seed
        self.ids: list[str] = []
        self.vectors: np.ndarray | None = None
        self._centroids: np.ndarray | None = None
        self._clusters: dict[int, list[int]] = {}

    def add(self, ids: list[str], vectors: np.ndarray):
        self.ids.extend(ids)
        self.vectors = vectors if self.vectors is None else np.vstack([self.vectors, vectors])
        self._centroids = None  # invalidate, rebuild on next search

    def _build(self):
        self._centroids, assignments = _kmeans(self.vectors, self.nlist, iters=15, seed=self.seed)
        self._clusters = {c: [] for c in range(self.nlist)}
        for i, c in enumerate(assignments):
            self._clusters[int(c)].append(i)

    def search(self, query: np.ndarray, k: int) -> list[tuple[str, float]]:
        if self._centroids is None:
            self._build()

        centroid_dists = np.linalg.norm(self._centroids - query, axis=1)
        probe_clusters = np.argsort(centroid_dists)[:self.nprobe]
        candidate_idx = [i for c in probe_clusters for i in self._clusters[int(c)]]
        if not candidate_idx:
            return []

        candidate_vectors = self.vectors[candidate_idx]
        scores = self.metric.score(query, candidate_vectors)
        top = np.argsort(-scores)[:k]
        return [(self.ids[candidate_idx[i]], float(scores[i])) for i in top]


class VectorStore:
    """User-facing wrapper: owns id -> metadata, delegates the actual nearest-neighbor
    work to whichever VectorIndex it was configured with."""

    def __init__(self, index: VectorIndex):
        self.index = index
        self.metadata: dict[str, dict] = {}

    def add(self, ids: list[str], vectors: np.ndarray, metadata: list[dict] | None = None):
        self.index.add(ids, vectors)
        for i, id_ in enumerate(ids):
            self.metadata[id_] = (metadata[i] if metadata else {})

    def search(self, query: np.ndarray, k: int = 5):
        return [(id_, score, self.metadata.get(id_, {})) for id_, score in self.index.search(query, k)]


def make_clustered_dataset(n_clusters: int, per_cluster: int, dim: int, seed: int):
    # Deliberately noisy relative to the center spread (not neatly separated blobs) -
    # cleanly separated clusters make IVF look artificially perfect and hide the
    # recall/speed trade-off that's the whole point of using an approximate index.
    rng = np.random.default_rng(seed)
    centers = rng.uniform(-3, 3, size=(n_clusters, dim))
    ids, vectors, labels = [], [], []
    for c in range(n_clusters):
        pts = centers[c] + rng.normal(scale=3.5, size=(per_cluster, dim))
        for j, p in enumerate(pts):
            ids.append(f"doc-{c}-{j}")
            vectors.append(p)
            labels.append(c)
    return ids, np.array(vectors), labels


def recall_at_k(ground_truth: list[tuple], candidate: list[tuple]) -> float:
    gt_ids = {row[0] for row in ground_truth}
    hit_ids = {row[0] for row in candidate}
    return len(gt_ids & hit_ids) / len(gt_ids) if gt_ids else 1.0


def main():
    n_clusters, per_cluster, dim = 10, 20, 8
    ids, vectors, labels = make_clustered_dataset(n_clusters, per_cluster, dim, seed=0)
    print(f"dataset: {len(ids)} vectors, dim={dim}, {n_clusters} natural (noisy, overlapping) clusters")

    metric = CosineSimilarity()
    brute = VectorStore(BruteForceIndex(metric))
    nprobe = 2
    ivf = VectorStore(IVFIndex(metric, nlist=n_clusters, nprobe=nprobe, seed=1))

    meta = [{"cluster": c} for c in labels]
    brute.add(ids, vectors, meta)
    ivf.add(ids, vectors, meta)

    rng = np.random.default_rng(99)
    k = 5
    recalls = []
    print(f"\ntop-{k} search, brute force vs IVF (nlist={n_clusters}, nprobe={nprobe}):")
    for q_idx in rng.choice(len(ids), size=6, replace=False):
        query = vectors[q_idx]
        gt = brute.search(query, k)
        approx = ivf.search(query, k)
        r = recall_at_k(gt, approx)
        recalls.append(r)
        print(f"  query={ids[q_idx]:<10} brute_top1={gt[0][0]:<10} ivf_top1={approx[0][0]:<10} recall@{k}={r:.2f}")

    avg_recall = sum(recalls) / len(recalls)
    print(f"\naverage recall@{k} of IVF vs brute force: {avg_recall:.2f}")

    # A vector always finds itself as its own nearest neighbor under cosine similarity -
    # a cheap, independent sanity check on the brute-force path itself.
    probe = vectors[0]
    self_hit = brute.search(probe, k=1)[0][0]
    assert self_hit == ids[0], "brute force failed the trivial self-match check"

    assert avg_recall >= 0.7, f"IVF recall too low ({avg_recall:.2f}) - index/params need tuning"
    print(f"\nself-check passed: brute force self-match correct, IVF recall@{k} = {avg_recall:.2f} (>= 0.70 threshold).")


if __name__ == "__main__":
    main()
