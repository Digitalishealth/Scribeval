"""Tests for multi-run variance reporting."""

from __future__ import annotations

import pytest

from scribeval.pipeline import EvaluationPipeline
from tests.conftest import RUBRICS_DIR, MockJudge


def test_runs_must_be_positive(sample_case) -> None:
    with pytest.raises(ValueError):
        EvaluationPipeline(
            dimensions=["omission"],
            judge=MockJudge(),
            rubric_dir=RUBRICS_DIR,
            runs=0,
        )


def test_single_run_has_no_run_statistics(sample_case) -> None:
    pipeline = EvaluationPipeline(
        dimensions=["omission"],
        judge=MockJudge(),
        rubric_dir=RUBRICS_DIR,
        runs=1,
    )
    report = pipeline.evaluate_case(sample_case)
    assert report.run_statistics == []


def test_multi_run_populates_run_statistics(sample_case) -> None:
    pipeline = EvaluationPipeline(
        dimensions=["omission", "hallucination"],
        judge=MockJudge(),
        rubric_dir=RUBRICS_DIR,
        runs=3,
    )
    report = pipeline.evaluate_case(sample_case)
    assert len(report.run_statistics) == 2
    for stats in report.run_statistics:
        assert stats.run_count == 3
        assert len(stats.per_run_scores) == 3
        # With a deterministic mock the std must be exactly 0.
        assert stats.std_score == 0.0
        assert stats.mean_score == pytest.approx(stats.per_run_scores[0])


def test_reproducibility_metadata_populated(sample_case) -> None:
    pipeline = EvaluationPipeline(
        dimensions=["omission"],
        judge=MockJudge(),
        rubric_dir=RUBRICS_DIR,
    )
    report = pipeline.evaluate_case(sample_case)
    assert report.reproducibility is not None
    assert report.reproducibility.transcript_hash
    assert "omission" in report.reproducibility.rubric_hashes


def test_report_notice_disclaims_medical_device(sample_case) -> None:
    pipeline = EvaluationPipeline(
        dimensions=["omission"],
        judge=MockJudge(),
        rubric_dir=RUBRICS_DIR,
    )
    report = pipeline.evaluate_case(sample_case)
    assert "NOT A MEDICAL DEVICE" in report.notice
