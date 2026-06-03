"""Report models: evaluation reports and aggregate statistics."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from scribeval.models.score import DimensionScore, SeverityLevel
from scribeval.reproducibility import ReproducibilityMetadata


class DimensionRunStatistics(BaseModel):
    """Statistics across repeated runs of the same dimension.

    Populated when `scribeval evaluate --runs N` is used. The run-level
    mean is used as the canonical score; the standard deviation and CI
    quantify judge variance so reviewers can see how stable the score is.
    """

    dimension: str
    run_count: int
    mean_score: float
    std_score: float
    ci95_low: float
    ci95_high: float
    per_run_scores: list[float]


class EvaluationReport(BaseModel):
    """Complete evaluation report for a single case."""

    report_id: str
    case_id: str
    scribe_product: str | None = None
    candidate_label: str | None = None
    consultation_type: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    dimension_scores: list[DimensionScore]
    overall_score: float = Field(ge=0.0, le=1.0)
    overall_severity: SeverityLevel
    summary: str
    data_flow_disclosure: str
    scribeval_version: str
    reproducibility: ReproducibilityMetadata | None = None
    run_statistics: list[DimensionRunStatistics] = Field(default_factory=list)
    specialty_weight_multipliers: dict[str, float] = Field(default_factory=dict)
    notice: str = (
        "NOT A MEDICAL DEVICE. Scribeval produces indicative quality and "
        "safety signals for transcript-to-note documentation quality. It is not clinically "
        "validated, not TGA-registered, and must not be used as the sole "
        "basis for clinical, procurement, or regulatory decisions. See the "
        "project README for disclaimers and limitations."
    )


class DimensionStatistics(BaseModel):
    """Aggregate statistics for a single dimension across multiple cases."""

    dimension: str
    mean: float
    std: float
    median: float
    min_score: float
    max_score: float
    critical_finding_count: int
    case_scores: list[float]


class AggregateReport(BaseModel):
    """Statistical aggregation across multiple evaluation cases."""

    report_id: str
    case_count: int
    scribe_product: str | None = None
    dimension_statistics: dict[str, DimensionStatistics]
    overall_mean: float
    overall_std: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
