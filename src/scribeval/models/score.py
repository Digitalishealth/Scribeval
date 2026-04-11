"""Scoring models: dimension scores, evidence findings, and severity levels."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class SeverityLevel(StrEnum):
    """Severity classification for findings."""

    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class Evidence(BaseModel):
    """A specific finding supporting a dimension score."""

    description: str
    severity: SeverityLevel
    transcript_excerpt: str | None = None
    note_excerpt: str | None = None
    clinical_impact: str | None = None


class DimensionScore(BaseModel):
    """Score for a single evaluation dimension.

    All scores are normalised 0-1 where 1 = perfect (no issues found).
    """

    dimension: str
    score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    severity_summary: SeverityLevel
    findings: list[Evidence] = Field(default_factory=list)
    reasoning: str
    rubric_version: str
    judge_type: str
    judge_model: str | None = None
    raw_judge_response: str | None = None
