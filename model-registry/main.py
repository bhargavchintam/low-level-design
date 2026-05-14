"""Model registry demo - MLflow-style register/version/stage-transition, State pattern for stages."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class Stage(Enum):
    NONE = "None"
    STAGING = "Staging"
    PRODUCTION = "Production"
    ARCHIVED = "Archived"


# Explicit state machine: which stage moves are legal. Keeping this as data
# (rather than if/elif chains inside transition_stage) is what makes it a
# State pattern rather than a pile of conditionals - new stages/rules only
# touch this table.
_ALLOWED_TRANSITIONS: dict[Stage, set[Stage]] = {
    Stage.NONE: {Stage.STAGING, Stage.ARCHIVED},
    Stage.STAGING: {Stage.PRODUCTION, Stage.ARCHIVED, Stage.NONE},
    Stage.PRODUCTION: {Stage.ARCHIVED, Stage.STAGING},
    Stage.ARCHIVED: {Stage.NONE, Stage.STAGING},
}


class InvalidTransition(Exception):
    pass


@dataclass
class ModelVersion:
    name: str
    version: int
    source: str
    run_metrics: dict = field(default_factory=dict)
    stage: Stage = Stage.NONE
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"v{self.version}[{self.stage.value}] ({self.source})"


class RegisteredModel:
    """All versions registered under one model name."""

    def __init__(self, name: str):
        self.name = name
        self.versions: dict[int, ModelVersion] = {}
        self._next_version = 1

    def add_version(self, source: str, run_metrics: dict) -> ModelVersion:
        mv = ModelVersion(self.name, self._next_version, source, run_metrics)
        self.versions[mv.version] = mv
        self._next_version += 1
        return mv


class ModelRegistry:
    def __init__(self):
        self._models: dict[str, RegisteredModel] = {}

    def register_model(self, name: str) -> RegisteredModel:
        if name not in self._models:
            self._models[name] = RegisteredModel(name)
        return self._models[name]

    def create_version(self, name: str, source: str, run_metrics: dict | None = None) -> ModelVersion:
        model = self.register_model(name)
        return model.add_version(source, run_metrics or {})

    def get_version(self, name: str, version: int) -> ModelVersion:
        return self._models[name].versions[version]

    def transition_stage(self, name: str, version: int, target: Stage) -> ModelVersion:
        mv = self.get_version(name, version)
        if target not in _ALLOWED_TRANSITIONS[mv.stage]:
            raise InvalidTransition(f"{mv.stage.value} -> {target.value} is not allowed")

        # MLflow semantics: a model can have only one Production version at a
        # time, so promoting one demotes the incumbent to Archived instead of
        # leaving two versions claiming to be prod.
        if target == Stage.PRODUCTION:
            for other in self._models[name].versions.values():
                if other.version != version and other.stage == Stage.PRODUCTION:
                    other.stage = Stage.ARCHIVED

        mv.stage = target
        return mv

    def get_by_stage(self, name: str, stage: Stage) -> list[ModelVersion]:
        return sorted(
            (mv for mv in self._models[name].versions.values() if mv.stage == stage),
            key=lambda mv: mv.version,
        )

    def latest_version(self, name: str) -> ModelVersion:
        return max(self._models[name].versions.values(), key=lambda mv: mv.version)


def main():
    registry = ModelRegistry()

    v1 = registry.create_version("fraud-detector", "s3://models/fraud/v1.pkl", {"auc": 0.81})
    v2 = registry.create_version("fraud-detector", "s3://models/fraud/v2.pkl", {"auc": 0.86})
    v3 = registry.create_version("fraud-detector", "s3://models/fraud/v3.pkl", {"auc": 0.90})
    print("registered:", v1, v2, v3)

    registry.transition_stage("fraud-detector", 1, Stage.STAGING)
    registry.transition_stage("fraud-detector", 1, Stage.PRODUCTION)
    print("\nafter promoting v1 to Production:")
    print("  production:", registry.get_by_stage("fraud-detector", Stage.PRODUCTION))

    registry.transition_stage("fraud-detector", 2, Stage.STAGING)
    registry.transition_stage("fraud-detector", 2, Stage.PRODUCTION)
    print("\nafter promoting v2 to Production (should auto-archive v1):")
    print("  production:", registry.get_by_stage("fraud-detector", Stage.PRODUCTION))
    print("  archived:  ", registry.get_by_stage("fraud-detector", Stage.ARCHIVED))

    registry.transition_stage("fraud-detector", 3, Stage.STAGING)
    print("\nafter staging v3:")
    print("  staging:   ", registry.get_by_stage("fraud-detector", Stage.STAGING))
    print("  latest:    ", registry.latest_version("fraud-detector"))

    print("\nrejecting an illegal jump (None -> Production directly):")
    v4 = registry.create_version("fraud-detector", "s3://models/fraud/v4.pkl", {"auc": 0.77})
    try:
        registry.transition_stage("fraud-detector", v4.version, Stage.PRODUCTION)
    except InvalidTransition as e:
        print(f"  rejected as expected: {e}")

    assert len(registry.get_by_stage("fraud-detector", Stage.PRODUCTION)) == 1
    assert registry.get_by_stage("fraud-detector", Stage.PRODUCTION)[0].version == 2
    assert registry.get_version("fraud-detector", 1).stage == Stage.ARCHIVED
    print("\nself-check passed: exactly one Production version, old one archived.")


if __name__ == "__main__":
    main()
