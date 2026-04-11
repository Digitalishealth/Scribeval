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
