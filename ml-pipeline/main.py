"""sklearn-style ML pipeline - chained transformers (impute, scale, encode) feeding a final
estimator, with fit/transform on the training set and transform-only (no refitting) at predict time."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, replace

import numpy as np


@dataclass
class Dataset:
    numeric: np.ndarray       # (n_samples, n_numeric), float64, may contain NaN
    categorical: np.ndarray   # (n_samples, n_categorical), string


class Transformer(ABC):
    @abstractmethod
    def fit(self, data: Dataset) -> "Transformer":
        ...

    @abstractmethod
    def transform(self, data: Dataset) -> Dataset:
        ...

    def fit_transform(self, data: Dataset) -> Dataset:
        return self.fit(data).transform(data)


class SimpleImputer(Transformer):
    """Fills missing numeric values with the column mean learned at fit time."""

    def __init__(self):
        self._means: np.ndarray | None = None

    def fit(self, data: Dataset) -> "SimpleImputer":
        self._means = np.nanmean(data.numeric, axis=0)
        return self

    def transform(self, data: Dataset) -> Dataset:
        numeric = data.numeric.copy()
        rows, cols = np.where(np.isnan(numeric))
        numeric[rows, cols] = self._means[cols]
        return replace(data, numeric=numeric)


class StandardScaler(Transformer):
    """Zero-mean, unit-variance scaling per numeric column, using statistics from fit time only."""

    def __init__(self):
        self._mean: np.ndarray | None = None
        self._std: np.ndarray | None = None

    def fit(self, data: Dataset) -> "StandardScaler":
        self._mean = data.numeric.mean(axis=0)
        std = data.numeric.std(axis=0)
        std[std == 0] = 1.0
        self._std = std
        return self

    def transform(self, data: Dataset) -> Dataset:
        return replace(data, numeric=(data.numeric - self._mean) / self._std)


class OneHotEncoder(Transformer):
    """Encodes each categorical column into one-hot columns using the categories seen at fit time,
    then folds the result into `numeric` - the terminal step before an estimator that only
    understands numeric arrays. Unseen test-time categories simply encode to an all-zero block."""

    def __init__(self):
        self._categories: list[np.ndarray] | None = None

    def fit(self, data: Dataset) -> "OneHotEncoder":
        self._categories = [np.unique(data.categorical[:, c]) for c in range(data.categorical.shape[1])]
        return self

    def transform(self, data: Dataset) -> Dataset:
        blocks = []
        for c, categories in enumerate(self._categories):
            column = data.categorical[:, c]
            blocks.append((column[:, None] == categories[None, :]).astype(float))
        merged = np.hstack([data.numeric, *blocks])
        return Dataset(numeric=merged, categorical=np.empty((merged.shape[0], 0), dtype=str))


class Estimator(ABC):
    @abstractmethod
    def fit(self, X: np.ndarray, y: np.ndarray) -> "Estimator":
        ...

    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        ...


class KNNClassifier(Estimator):
    """k-nearest-neighbors on Euclidean distance - majority vote over the k closest training rows."""

    def __init__(self, k: int = 3):
        self.k = k
        self._X: np.ndarray | None = None
        self._y: np.ndarray | None = None

    def fit(self, X: np.ndarray, y: np.ndarray) -> "KNNClassifier":
        self._X, self._y = X, y
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        preds = []
        for row in X:
            distances = np.linalg.norm(self._X - row, axis=1)
            nearest = np.argsort(distances)[: self.k]
            preds.append(np.bincount(self._y[nearest]).argmax())
        return np.array(preds)


class Pipeline:
    """Chains transformers, then a final estimator. `fit` runs fit_transform through every step so
    each one learns only from the training set; `predict` runs transform-only, so test data is
    scaled/imputed/encoded using statistics the pipeline already learned, never refit on it."""

    def __init__(self, steps: list[tuple[str, Transformer]], estimator: Estimator):
        self.steps = steps
        self.estimator = estimator

    def fit(self, data: Dataset, y: np.ndarray) -> "Pipeline":
        transformed = data
        for _, step in self.steps:
            transformed = step.fit_transform(transformed)
        self.estimator.fit(transformed.numeric, y)
        return self

    def transform(self, data: Dataset) -> Dataset:
        transformed = data
        for _, step in self.steps:
            transformed = step.transform(transformed)
        return transformed

    def predict(self, data: Dataset) -> np.ndarray:
        return self.estimator.predict(self.transform(data).numeric)


def main():
    # income (some missing), age -> numeric; employment_type -> categorical; y: loan approved (1/0)
    train_numeric = np.array(
        [
            [72000, 34], [65000, 29], [np.nan, 41], [58000, 25], [91000, 38],
            [30000, 22], [27000, 45], [np.nan, 31], [110000, 50], [48000, 27],
            [83000, 36], [25000, 23],
        ],
        dtype=float,
    )
    train_categorical = np.array(
        [["salaried"], ["salaried"], ["salaried"], ["self-employed"], ["salaried"],
         ["self-employed"], ["unemployed"], ["self-employed"], ["salaried"], ["self-employed"],
         ["salaried"], ["unemployed"]],
        dtype=str,
    )
    y_train = np.array([1, 1, 1, 0, 1, 0, 0, 0, 1, 0, 1, 0])

    test_numeric = np.array([[70000, 33], [np.nan, 24], [98000, 40], [28000, 40]], dtype=float)
    test_categorical = np.array([["salaried"], ["unemployed"], ["salaried"], ["self-employed"]], dtype=str)
    y_test = np.array([1, 0, 1, 0])

    pipeline = Pipeline(
        steps=[
            ("impute", SimpleImputer()),
            ("scale", StandardScaler()),
            ("encode", OneHotEncoder()),
        ],
        estimator=KNNClassifier(k=3),
    )

    pipeline.fit(Dataset(train_numeric, train_categorical), y_train)

    predictions = pipeline.predict(Dataset(test_numeric, test_categorical))
    accuracy = (predictions == y_test).mean()

    print("-- test set predictions --")
    for i, (pred, actual) in enumerate(zip(predictions, y_test)):
        income, age = test_numeric[i]
        employment = test_categorical[i, 0]
        match = "correct" if pred == actual else "WRONG"
        print(f"  income={income:<8} age={age:<4} employment={employment:<14} "
              f"predicted={pred} actual={actual} ({match})")

    print(f"\naccuracy: {accuracy:.0%}")


if __name__ == "__main__":
    main()
