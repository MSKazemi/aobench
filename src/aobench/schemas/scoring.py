"""Scoring schema — weight profiles and scoring configuration."""

from __future__ import annotations

from pydantic import BaseModel, model_validator


class WeightProfile(BaseModel):
    """Named weight profile for aggregating dimension scores."""

    name: str
    version: str
    weights: dict[str, float]  # dimension -> weight (must sum to 1.0)

    @model_validator(mode="after")
    def weights_sum_to_one(self) -> "WeightProfile":
        total = sum(self.weights.values())
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"Weights must sum to 1.0, got {total:.4f}")
        return self


class ScoringConfig(BaseModel):
    profiles: dict[str, WeightProfile]  # profile name -> profile

    def get(self, name: str) -> WeightProfile:
        if name not in self.profiles:
            raise KeyError(f"Unknown weight profile: '{name}'. Available: {list(self.profiles)}")
        return self.profiles[name]
