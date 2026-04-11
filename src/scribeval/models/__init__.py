"""Data models for Scribeval evaluation inputs, scores, and reports."""

from scribeval.models.case import (
    ConsultationType,
    EvaluationCase,
    ReferenceNote,
    ScribeNote,
    Transcript,
)
from scribeval.models.report import AggregateReport, DimensionStatistics, EvaluationReport
from scribeval.models.score import DimensionScore, Evidence, SeverityLevel

__all__ = [
    "ConsultationType",
    "EvaluationCase",
    "ReferenceNote",
    "ScribeNote",
    "Transcript",
    "DimensionScore",
    "Evidence",
    "SeverityLevel",
    "EvaluationReport",
    "AggregateReport",
    "DimensionStatistics",
]
