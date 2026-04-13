"""Tests for sensitivity analysis on completed reports."""

from __future__ import annotations

from scribeval.pipeline import EvaluationPipeline
from scribeval.sensitivity import sensitivity_analysis
from tests.conftest import RUBRICS_DIR


def _report(case, judge):
    pipeline = EvaluationPipeline(
        dimensions=["omission", "hallucination"],
        judge=judge,
        rubric_dir=RUBRICS_DIR,
    )
    return pipeline.evaluate_case(case)


def test_sensitivity_baseline_score_matches_report(sample_case, perfect_mock_judge) -> None:
    report = _report(sample_case, perfect_mock_judge)
    result = sensitivity_analysis(report)
    assert result.baseline_score == report.overall_score


def test_sensitivity_includes_uniform_weights_scenario(sample_case, mock_judge) -> None:
    report = _report(sample_case, mock_judge)
    result = sensitivity_analysis(report)
    names = [s["name"] for s in result.scenarios]
    assert "uniform_weights" in names


def test_sensitivity_flags_robust_for_perfect_scores(sample_case, perfect_mock_judge) -> None:
    report = _report(sample_case, perfect_mock_judge)
    result = sensitivity_analysis(report)
    # A report with no findings and perfect scores across all dimensions
    # should not wobble more than 0.10 under any reasonable perturbation.
    assert result.robust is True
    assert result.score_range <= 0.10


def test_sensitivity_produces_per_dimension_scenarios(sample_case, mock_judge) -> None:
    report = _report(sample_case, mock_judge)
    result = sensitivity_analysis(report, perturbation=0.20)
    # For 2 dimensions, expect 2 * 2 = 4 per-dim perturbations (0.8x, 1.2x each)
    # plus severity perturbations and the uniform baseline.
    dim_scenarios = [s for s in result.scenarios if "weight_" in s["name"]]
    assert len(dim_scenarios) >= 4
    severity_scenarios = [s for s in result.scenarios if "severity_penalty" in s["name"]]
    assert len(severity_scenarios) == 2  # 0.5x and 1.5x (1.0x skipped)
