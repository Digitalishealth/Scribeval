"""Sensitivity analysis on an existing EvaluationReport.

Takes a completed evaluation report and explores how the overall score
would change if the dimension weights or severity penalty were
perturbed. The goal is to surface whether a score is robust ("even if
you halved the hallucination weight, the result is the same") or
fragile ("swap two weights and the ranking inverts").

This is CHEAP — it does not re-run the judge. It re-uses the
per-dimension scores already in the report and only changes the
aggregation parameters.

Use cases:
- A scribe vendor asks "why is our score 0.73?" — sensitivity analysis
  lets you show them that any reasonable weighting produces 0.70-0.76,
  not just your specific choice.
- A reviewer critiques the weights as arbitrary — sensitivity analysis
  demonstrates whether the critique actually moves the answer.
"""

from __future__ import annotations

from dataclasses import dataclass

from scribeval.models.report import EvaluationReport
from scribeval.models.score import DimensionScore
from scribeval.pipeline import (
    DIMENSION_WEIGHTS,
    compute_severity_penalty,
)


@dataclass
class SensitivityResult:
    """Summary of how an overall score moves under weight perturbations."""

    baseline_score: float
    min_score: float
    max_score: float
    score_range: float
    robust: bool  # True if range <= 0.10
    scenarios: list[dict]


def _weighted_overall(
    scores: list[DimensionScore],
    weights: dict[str, float],
    severity_multiplier: float,
) -> float:
    """Re-compute overall score with arbitrary weights and severity scaling."""
    if not scores:
        return 0.0
    total_weight = 0.0
    weighted_sum = 0.0
    for s in scores:
        w = weights.get(s.dimension, 1.0)
        weighted_sum += s.score * w
        total_weight += w
    base = weighted_sum / total_weight if total_weight > 0 else 0.0
    penalty = compute_severity_penalty(scores) * severity_multiplier
    penalty = max(0.0, min(0.60, penalty))
    return round(max(base * (1.0 - penalty), 0.0), 4)


def sensitivity_analysis(
    report: EvaluationReport,
    perturbation: float = 0.20,
) -> SensitivityResult:
    """Run a grid of weight perturbations on a completed report.

    For each dimension present in the report, multiply its weight by
    (1 - perturbation), (1.0), and (1 + perturbation). Also scale the
    severity penalty from 0.5x to 1.5x. Collect every resulting overall
    score and report the min, max, and range.
    """
    dims = [s.dimension for s in report.dimension_scores]
    scenarios: list[dict] = []

    perturb_factors = [1.0 - perturbation, 1.0, 1.0 + perturbation]
    penalty_factors = [0.5, 1.0, 1.5]

    # All-uniform baseline (every dimension weight = 1.0) — this is the
    # "what if I didn't weight anything" reference point.
    uniform_weights = {d: 1.0 for d in dims}
    uniform_score = _weighted_overall(report.dimension_scores, uniform_weights, 1.0)
    scenarios.append(
        {
            "name": "uniform_weights",
            "description": "All dimensions weighted equally",
            "overall_score": uniform_score,
        }
    )

    # Per-dimension perturbation: vary each dimension's weight independently
    for dim in dims:
        base_weight = DIMENSION_WEIGHTS.get(dim, 1.0)
        for factor in perturb_factors:
            if factor == 1.0:
                continue
            perturbed = {d: DIMENSION_WEIGHTS.get(d, 1.0) for d in dims}
            perturbed[dim] = base_weight * factor
            sc = _weighted_overall(report.dimension_scores, perturbed, 1.0)
            scenarios.append(
                {
                    "name": f"{dim}_weight_{factor}x",
                    "description": f"{dim} weight scaled by {factor}",
                    "overall_score": sc,
                }
            )

    # Severity penalty perturbation
    for sp in penalty_factors:
        if sp == 1.0:
            continue
        base_weights = {d: DIMENSION_WEIGHTS.get(d, 1.0) for d in dims}
        sc = _weighted_overall(report.dimension_scores, base_weights, sp)
        scenarios.append(
            {
                "name": f"severity_penalty_{sp}x",
                "description": f"Severity penalty scaled by {sp}",
                "overall_score": sc,
            }
        )

    all_scores = [s["overall_score"] for s in scenarios] + [report.overall_score]
    score_min = min(all_scores)
    score_max = max(all_scores)
    score_range = round(score_max - score_min, 4)

    return SensitivityResult(
        baseline_score=report.overall_score,
        min_score=round(score_min, 4),
        max_score=round(score_max, 4),
        score_range=score_range,
        robust=score_range <= 0.10,
        scenarios=scenarios,
    )
