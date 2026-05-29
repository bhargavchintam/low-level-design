"""PyTorch-style Dataset + DataLoader - Iterator pattern for batching, Decorator/Composite
for chained transforms. DataLoader knows nothing about what a sample "means"; it only
knows how to fetch indices from a Dataset and stack them into batches.
"""

import numpy as np
from abc import ABC, abstractmethod


class Dataset(ABC):
    @abstractmethod
    def __len__(self) -> int:
        ...

    @abstractmethod
    def __getitem__(self, index: int):
        ...


class Compose:
    """Chains transforms into one callable - Composite over the Transform interface."""

    def __init__(self, transforms: list):
        self.transforms = transforms

    def __call__(self, x):
        for t in self.transforms:
            x = t(x)
        return x


class Normalize:
    def __init__(self, mean: np.ndarray, std: np.ndarray):
        self.mean = mean
        self.std = std

    def __call__(self, x: np.ndarray) -> np.ndarray:
        return (x - self.mean) / self.std


class AddGaussianNoise:
    """Seeded per-instance RNG so repeated __call__s are reproducible across runs."""

    def __init__(self, std: float, seed: int = 0):
        self.std = std
        self._rng = np.random.default_rng(seed)

    def __call__(self, x: np.ndarray) -> np.ndarray:
        return x + self._rng.normal(0, self.std, size=x.shape)


class ArrayDataset(Dataset):
    """Wraps feature/label arrays; the dataset owns its transform, matching torchvision's
    convention (Dataset applies transform in __getitem__, DataLoader stays agnostic to it)."""

    def __init__(self, features: np.ndarray, labels: np.ndarray, transform=None):
        assert len(features) == len(labels)
        self.features = features
        self.labels = labels
        self.transform = transform

    def __len__(self) -> int:
        return len(self.features)

    def __getitem__(self, index: int):
        x = self.features[index]
        if self.transform is not None:
            x = self.transform(x)
        return x, self.labels[index]


def default_collate(samples: list[tuple[np.ndarray, np.ndarray]]):
    xs, ys = zip(*samples)
    return np.stack(xs), np.stack(ys)


class DataLoader:
    def __init__(self, dataset: Dataset, batch_size: int, shuffle: bool = False,
                 drop_last: bool = False, seed: int | None = None, collate_fn=default_collate):
        self.dataset = dataset
        self.batch_size = batch_size
        self.shuffle = shuffle
        self.drop_last = drop_last
        self.collate_fn = collate_fn
        self._rng = np.random.default_rng(seed)

    def __iter__(self):
        order = np.arange(len(self.dataset))
        if self.shuffle:
            self._rng.shuffle(order)  # fresh permutation each epoch, in-place on a copy

        for start in range(0, len(order), self.batch_size):
            batch_idx = order[start:start + self.batch_size]
            if self.drop_last and len(batch_idx) < self.batch_size:
                break
            samples = [self.dataset[i] for i in batch_idx]
            yield self.collate_fn(samples)

    def __len__(self) -> int:
        n = len(self.dataset)
        if self.drop_last:
            return n // self.batch_size
        return -(-n // self.batch_size)  # ceil division


def main():
    n_samples, n_features = 23, 4
    rng = np.random.default_rng(42)
    features = rng.normal(loc=5.0, scale=2.0, size=(n_samples, n_features))
    labels = np.arange(n_samples)  # label = original index, so coverage is easy to verify

    mean, std = features.mean(axis=0), features.std(axis=0)
    transform = Compose([Normalize(mean, std), AddGaussianNoise(std=0.01, seed=1)])
    dataset = ArrayDataset(features, labels, transform=transform)

    loader = DataLoader(dataset, batch_size=5, shuffle=True, drop_last=False, seed=0)
    print(f"dataset size={len(dataset)}  batch_size={loader.batch_size}  batches/epoch={len(loader)}")

    for epoch in range(2):
        print(f"\n--- epoch {epoch} ---")
        seen_labels = []
        for b, (xb, yb) in enumerate(loader):
            seen_labels.extend(yb.tolist())
            print(f"  batch {b}: x.shape={xb.shape}  labels={yb.tolist()}")
        assert sorted(seen_labels) == list(range(n_samples)), "epoch didn't cover every sample exactly once"
        print(f"  epoch order (first 10 labels seen): {seen_labels[:10]}")

    print("\n--- drop_last=True, batch_size=5 (23 samples -> 4 full batches, 3 dropped) ---")
    strict_loader = DataLoader(dataset, batch_size=5, shuffle=False, drop_last=True)
    total = 0
    for xb, yb in strict_loader:
        total += len(yb)
        assert len(yb) == 5
    print(f"  yielded {total} samples across {len(strict_loader)} batches (all full-sized)")

    print("\nself-check passed: every epoch is a full permutation of the dataset, "
          "drop_last correctly discards the trailing partial batch.")


if __name__ == "__main__":
    main()
