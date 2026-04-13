"""YAML rubric loading and Pydantic validation."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class ScoringConfig(BaseModel):
    """Scoring configuration within a rubric."""

    scale: str = "0_to_1"
    direction: str = "higher_is_better"


class SeverityCriterion(BaseModel):
    """Definition of a severity level within a rubric."""

    description: str
    examples: list[str] = Field(default_factory=list)


class SpecialtyOverlay(BaseModel):
    """Per-specialty rubric adjustments.

    A specialty overlay does NOT replace the base rubric — it adds
    specialty-specific considerations and adjusts the weight of the
    dimension for that specialty. This lets a single rubric capture
    "omission matters 30% more in ED than in routine GP" without
    duplicating the whole rubric.

    Fields:
    - weight_multiplier: dimension weight multiplier for this specialty
      (e.g., 1.3 for ED hallucination). Applied to the base
      DIMENSION_WEIGHTS entry.
    - additional_criteria: extra text prepended to the evaluation
      instructions when this specialty is evaluated. Used for things
      like "in psychiatry, documentation of mental state exam is
      critical."
    - severity_escalation: list of severity levels to escalate by one
      tier for this specialty. E.g., ["moderate"] means findings the
      base rubric would call moderate become high for this specialty.
    """

    weight_multiplier: float = 1.0
    additional_criteria: str = ""
    severity_escalation: list[str] = Field(default_factory=list)


class RubricSchema(BaseModel):
    """Schema for a YAML evaluation rubric."""

    dimension: str
    version: str
    display_name: str
    description: str
    references: list[str] = Field(default_factory=list)
    scoring: ScoringConfig
    severity_criteria: dict[str, SeverityCriterion]
    evaluation_instructions: str
    australian_context: str
    specialty_overlays: dict[str, SpecialtyOverlay] = Field(default_factory=dict)

    def for_specialty(self, consultation_type: str) -> RubricSchema:
        """Return a rubric copy with the specialty overlay applied.

        If no overlay is defined for this consultation type, returns
        the unmodified rubric. Otherwise prepends the overlay's
        additional_criteria to the evaluation instructions. The
        weight_multiplier is NOT applied here — it is consumed by
        the pipeline's overall-score computation.
        """
        overlay = self.specialty_overlays.get(consultation_type)
        if overlay is None:
            return self
        new_instructions = self.evaluation_instructions
        if overlay.additional_criteria.strip():
            new_instructions = (
                f"## Specialty-specific considerations ({consultation_type})\n"
                f"{overlay.additional_criteria.strip()}\n\n"
                f"{self.evaluation_instructions}"
            )
        return self.model_copy(update={"evaluation_instructions": new_instructions})

    def specialty_weight_multiplier(self, consultation_type: str) -> float:
        overlay = self.specialty_overlays.get(consultation_type)
        if overlay is None:
            return 1.0
        return overlay.weight_multiplier


def load_rubric(path: Path) -> RubricSchema:
    """Load and validate a single rubric YAML file."""
    with open(path) as f:
        data = yaml.safe_load(f)
    return RubricSchema(**data)


def load_all_rubrics(directory: Path) -> dict[str, RubricSchema]:
    """Load all rubric YAML files from a directory."""
    rubrics = {}
    for path in sorted(directory.glob("*.yaml")):
        rubric = load_rubric(path)
        rubrics[rubric.dimension] = rubric
    return rubrics
