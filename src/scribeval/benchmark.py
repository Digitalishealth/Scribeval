"""Multi-case benchmark aggregation for transcript-to-note product comparison."""

from __future__ import annotations

import statistics
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from scribeval.compare import (
    MAX_SUBMISSIONS,
    MIN_SUBMISSIONS,
    BlindedReport,
    NoteSubmission,
    run_blinded_comparison,
)
from scribeval.models.case import ConsultationType
from scribeval.models.score import SeverityLevel
from scribeval.pipeline import EvaluationPipeline


@dataclass(frozen=True)
class BenchmarkCase:
    """One benchmark case with a shared transcript and candidate submissions."""

    case_id: str
    transcript_content: str
    submissions: list[NoteSubmission]
    consultation_type: ConsultationType = ConsultationType.GP_STANDARD
    reference_note_content: str | None = None


class BenchmarkCaseResult(BaseModel):
    """A single case's blinded comparison result."""

    case_id: str
    comparison: BlindedReport


class BenchmarkSubmissionSummary(BaseModel):
    """Aggregate performance for one unblinded submission label."""

    submission_label: str
    case_count: int
    mean_overall_score: float
    std_overall_score: float
    min_overall_score: float
    max_overall_score: float
    critical_finding_count: int
    scores_by_case: dict[str, float] = Field(default_factory=dict)
    dimension_mean_scores: dict[str, float] = Field(default_factory=dict)


class BenchmarkReport(BaseModel):
    """Aggregate benchmark report across multiple transcript-to-note cases."""

    benchmark_id: str
    case_count: int
    submission_summaries: dict[str, BenchmarkSubmissionSummary]
    ranking: list[tuple[str, float]]
    case_results: list[BenchmarkCaseResult]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


def run_benchmark(
    cases: list[BenchmarkCase],
    pipeline: EvaluationPipeline,
    rng_seed: int | None = None,
) -> BenchmarkReport:
    """Run blinded comparisons across cases and aggregate by submission label."""
    if not cases:
        raise ValueError("At least one benchmark case is required.")

    expected_labels = {submission.label for submission in cases[0].submissions}
    if len(expected_labels) < MIN_SUBMISSIONS:
        raise ValueError(
            f"At least {MIN_SUBMISSIONS} submissions are required for benchmarking."
        )
    if len(expected_labels) > MAX_SUBMISSIONS:
        raise ValueError(
            f"At most {MAX_SUBMISSIONS} submissions are supported for benchmarking."
        )

    for case in cases:
        labels = {submission.label for submission in case.submissions}
        if labels != expected_labels:
            raise ValueError(
                "Every benchmark case must include the same submission labels. "
                f"Expected {sorted(expected_labels)}, got {sorted(labels)} "
                f"for case {case.case_id!r}."
            )

    case_results: list[BenchmarkCaseResult] = []
    for idx, case in enumerate(cases):
        case_seed = None if rng_seed is None else rng_seed + idx
        comparison = run_blinded_comparison(
            transcript_content=case.transcript_content,
            submissions=case.submissions,
            pipeline=pipeline,
            consultation_type=case.consultation_type,
            reference_note_content=case.reference_note_content,
            rng_seed=case_seed,
        )
        case_results.append(
            BenchmarkCaseResult(case_id=case.case_id, comparison=comparison)
        )

    summaries = _summarise_submissions(case_results, expected_labels)
    ranking = sorted(
        (
            (label, summary.mean_overall_score)
            for label, summary in summaries.items()
        ),
        key=lambda item: item[1],
        reverse=True,
    )

    return BenchmarkReport(
        benchmark_id=uuid.uuid4().hex[:12],
        case_count=len(cases),
        submission_summaries=summaries,
        ranking=ranking,
        case_results=case_results,
    )


def _summarise_submissions(
    case_results: list[BenchmarkCaseResult],
    labels: set[str],
) -> dict[str, BenchmarkSubmissionSummary]:
    scores_by_label: dict[str, dict[str, float]] = {label: {} for label in labels}
    critical_by_label: dict[str, int] = {label: 0 for label in labels}
    dimension_scores: dict[str, dict[str, list[float]]] = {label: {} for label in labels}

    for case_result in case_results:
        comparison = case_result.comparison
        for blinded_label, single_report in comparison.per_label_reports.items():
            submission_label = comparison.label_to_submission[blinded_label]
            scores_by_label[submission_label][case_result.case_id] = (
                single_report.overall_score
            )
            critical_by_label[submission_label] += sum(
                1
                for dimension_score in single_report.dimension_scores
                for finding in dimension_score.findings
                if finding.severity == SeverityLevel.CRITICAL
            )
            for dimension_score in single_report.dimension_scores:
                per_dimension = dimension_scores[submission_label].setdefault(
                    dimension_score.dimension,
                    [],
                )
                per_dimension.append(dimension_score.score)

    summaries: dict[str, BenchmarkSubmissionSummary] = {}
    for label, case_scores in scores_by_label.items():
        scores = list(case_scores.values())
        dimension_means = {
            dimension: round(statistics.mean(values), 4)
            for dimension, values in sorted(dimension_scores[label].items())
            if values
        }
        summaries[label] = BenchmarkSubmissionSummary(
            submission_label=label,
            case_count=len(scores),
            mean_overall_score=round(statistics.mean(scores), 4),
            std_overall_score=round(
                statistics.stdev(scores), 4
            ) if len(scores) > 1 else 0.0,
            min_overall_score=round(min(scores), 4),
            max_overall_score=round(max(scores), 4),
            critical_finding_count=critical_by_label[label],
            scores_by_case={
                case_id: round(score, 4)
                for case_id, score in sorted(case_scores.items())
            },
            dimension_mean_scores=dimension_means,
        )

    return summaries
