"""Evaluation pipeline orchestration."""

from __future__ import annotations

import statistics
import uuid
from pathlib import Path

from scribeval import __version__
from scribeval.evaluators import EVALUATOR_REGISTRY, get_evaluator
from scribeval.judges.base import BaseJudge
from scribeval.judges.llm import LLMJudge
from scribeval.models.case import EvaluationCase
from scribeval.models.report import (
    AggregateReport,
    DimensionStatistics,
    EvaluationReport,
)
from scribeval.models.score import DimensionScore, SeverityLevel
from scribeval.rubrics.loader import load_all_rubrics

# Safety-critical dimensions receive higher weight in overall score
DIMENSION_WEIGHTS: dict[str, float] = {
    "omission": 1.5,
    "hallucination": 2.0,
    "medicolegal": 1.0,
    "ahpra": 1.0,
}

DEFAULT_RUBRIC_DIR = Path("rubrics")


def _generate_id() -> str:
    return uuid.uuid4().hex[:12]


def _compute_overall_score(scores: list[DimensionScore]) -> float:
    """Compute weighted average score across dimensions."""
    if not scores:
        return 0.0
    total_weight = 0.0
    weighted_sum = 0.0
    for s in scores:
        weight = DIMENSION_WEIGHTS.get(s.dimension, 1.0)
        weighted_sum += s.score * weight
        total_weight += weight
    return round(weighted_sum / total_weight, 4) if total_weight > 0 else 0.0


def _compute_overall_severity(scores: list[DimensionScore]) -> SeverityLevel:
    """Overall severity is the worst severity across all dimensions."""
    severity_order = list(SeverityLevel)
    worst = SeverityLevel.NONE
    for s in scores:
        if severity_order.index(s.severity_summary) > severity_order.index(worst):
            worst = s.severity_summary
    return worst


def _generate_summary(scores: list[DimensionScore]) -> str:
    """Generate a human-readable summary of evaluation results."""
    if not scores:
        return "No dimensions evaluated."

    overall = _compute_overall_score(scores)
    worst = _compute_overall_severity(scores)

    lines = [f"Overall score: {overall:.2f}/1.00 ({worst.value} severity)."]

    critical_findings = []
    for s in scores:
        for f in s.findings:
            if f.severity == SeverityLevel.CRITICAL:
                critical_findings.append(f"{s.dimension}: {f.description}")

    if critical_findings:
        lines.append(f"Critical findings ({len(critical_findings)}):")
        for cf in critical_findings:
            lines.append(f"  - {cf}")
    else:
        lines.append("No critical findings.")

    return "\n".join(lines)


def _data_flow_statement(judge: BaseJudge) -> str:
    """Generate explicit disclosure of data handling."""
    if isinstance(judge, LLMJudge):
        return (
            f"Evaluation performed using {judge.judge_model} via the Anthropic API. "
            "The consultation transcript and AI scribe output were sent to "
            "Anthropic's API for evaluation. Anthropic's data retention policy "
            "applies (see https://www.anthropic.com/policies). No data is stored "
            "by Scribeval beyond local report files. If a reference note was "
            "provided, it was also sent to the API for comparison."
        )
    return (
        f"Evaluation performed locally using {judge.judge_type} scoring. "
        "No clinical data was transmitted to external services."
    )


class EvaluationPipeline:
    """Orchestrates evaluation of AI scribe outputs across multiple dimensions."""

    def __init__(
        self,
        dimensions: list[str] | None = None,
        judge: BaseJudge | None = None,
        rubric_dir: Path | None = None,
    ):
        self.rubric_dir = rubric_dir or DEFAULT_RUBRIC_DIR
        self.rubrics = load_all_rubrics(self.rubric_dir)
        self.judge = judge or LLMJudge()
        self.dimensions = dimensions or list(EVALUATOR_REGISTRY.keys())

        # Validate requested dimensions
        for dim in self.dimensions:
            if dim not in EVALUATOR_REGISTRY:
                available = ", ".join(sorted(EVALUATOR_REGISTRY.keys()))
                raise ValueError(
                    f"Unknown dimension '{dim}'. Available: {available}"
                )
            if dim not in self.rubrics:
                raise ValueError(
                    f"No rubric found for dimension '{dim}' in {self.rubric_dir}"
                )

    def evaluate_case(self, case: EvaluationCase) -> EvaluationReport:
        """Run all configured evaluators against a single case."""
        scores: list[DimensionScore] = []
        for dim in self.dimensions:
            evaluator = get_evaluator(dim, self.rubrics[dim], self.judge)
            score = evaluator.evaluate(case)
            scores.append(score)

        return EvaluationReport(
            report_id=_generate_id(),
            case_id=case.case_id,
            scribe_product=case.scribe_note.scribe_product,
            consultation_type=case.consultation_type.value,
            dimension_scores=scores,
            overall_score=_compute_overall_score(scores),
            overall_severity=_compute_overall_severity(scores),
            summary=_generate_summary(scores),
            data_flow_disclosure=_data_flow_statement(self.judge),
            scribeval_version=__version__,
        )

    def evaluate_batch(self, cases: list[EvaluationCase]) -> AggregateReport:
        """Evaluate multiple cases and aggregate statistics."""
        reports = [self.evaluate_case(c) for c in cases]
        return self._aggregate(reports)

    def _aggregate(self, reports: list[EvaluationReport]) -> AggregateReport:
        """Compute aggregate statistics across multiple reports."""
        dim_scores: dict[str, list[float]] = {d: [] for d in self.dimensions}
        for report in reports:
            for ds in report.dimension_scores:
                if ds.dimension in dim_scores:
                    dim_scores[ds.dimension].append(ds.score)

        dim_stats: dict[str, DimensionStatistics] = {}
        for dim, scores in dim_scores.items():
            if not scores:
                continue
            critical_count = sum(
                1
                for report in reports
                for ds in report.dimension_scores
                if ds.dimension == dim
                for f in ds.findings
                if f.severity == SeverityLevel.CRITICAL
            )
            dim_stats[dim] = DimensionStatistics(
                dimension=dim,
                mean=round(statistics.mean(scores), 4),
                std=round(statistics.stdev(scores), 4) if len(scores) > 1 else 0.0,
                median=round(statistics.median(scores), 4),
                min_score=round(min(scores), 4),
                max_score=round(max(scores), 4),
                critical_finding_count=critical_count,
                case_scores=scores,
            )

        all_overall = [r.overall_score for r in reports]
        return AggregateReport(
            report_id=_generate_id(),
            case_count=len(reports),
            scribe_product=reports[0].scribe_product if reports else None,
            dimension_statistics=dim_stats,
            overall_mean=round(statistics.mean(all_overall), 4) if all_overall else 0.0,
            overall_std=(
                round(statistics.stdev(all_overall), 4)
                if len(all_overall) > 1
                else 0.0
            ),
        )
