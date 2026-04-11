"""Report models: evaluation reports and aggregate statistics."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from scribeval.models.score import DimensionScore, SeverityLevel


class EvaluationReport(BaseModel):
    """Complete evaluation report for a single case."""

    report_id: str
    case_id: str
    scribe_product: str | None = None
    consultation_type: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    dimension_scores: list[DimensionScore]
    overall_score: float = Field(ge=0.0, le=1.0)
    overall_severity: SeverityLevel
    summary: str
    data_flow_disclosure: str
    scribeval_version: str


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
