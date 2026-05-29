# ML Pipeline

## Problem
Design an sklearn-style pipeline: a sequence of transformers (impute missing values, scale numeric
features, one-hot encode categorical features) feeding a final estimator, where `fit` learns
statistics only from the training set and `predict` reuses those statistics on new data without
ever refitting on it - the same contract `sklearn.pipeline.Pipeline` gives you.

## Design
- `Dataset` - a fit/transform unit: a numeric matrix (may contain `NaN`) and a parallel categorical
  matrix.
- `Transformer` (ABC) - `fit(data)`, `transform(data)`, plus a default `fit_transform`.
- `SimpleImputer` - fills `NaN` in numeric columns with the column mean learned at fit time.
- `StandardScaler` - zero-mean, unit-variance scaling per numeric column, using fit-time statistics.
- `OneHotEncoder` - encodes categorical columns against the categories seen at fit time and folds
  the result into the numeric matrix - the last step before an estimator.
- `Estimator` (ABC) - `fit(X, y)`, `predict(X)`.
- `KNNClassifier` - k-nearest-neighbors by Euclidean distance, majority vote over the k closest
  training rows.
- `Pipeline` - holds an ordered list of transformer steps plus an estimator. `fit` runs
  `fit_transform` through every step then fits the estimator; `predict` runs `transform`-only
  through the same steps, so test data is imputed/scaled/encoded with training-set statistics.

## Patterns used
- **Strategy** - `Transformer` and `Estimator` are swappable interfaces; any transformer/estimator
  implementing the contract can be dropped into the pipeline.
- **Pipeline (Composite over Strategy)** - `Pipeline` composes an ordered chain of transformers and
  hides the step-by-step propagation behind two calls, `fit` and `predict`.

## How to run
```
cd /Users/bhargav/Desktop/low-level-design/ml-pipeline
python3 main.py
```
