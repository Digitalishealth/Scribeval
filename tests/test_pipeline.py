"""Tests for the evaluation pipeline."""

from __future__ import annotations

from pathlib import Path

from scribeval.models.case import EvaluationCase
from scribeval.models.score import SeverityLevel
from scribeval.pipeline import (
    EvaluationPipeline,
    _compute_overall_score,
    _compute_overall_severity,
)
from tests.conftest import MockJudge


class TestOverallScoreComputation:
    def test_weighted_average(self):
        from scribeval.models.score import DimensionScore

        scores = [
            DimensionScore(
                dimension="omission",
                score=0.8,
                confidence=0.9,
                severity_summary=SeverityLevel.LOW,
                reasoning="r",
                rubric_version="1.0",
                judge_type="mock",
            ),
            DimensionScore(
                dimension="hallucination",
                score=0.6,
                confidence=0.9,
                severity_summary=SeverityLevel.MODERATE,
                reasoning="r",
                rubric_version="1.0",
                judge_type="mock",
            ),
        ]
        # omission weight=1.5, hallucination weight=2.0
        # (0.8*1.5 + 0.6*2.0) / (1.5+2.0) = (1.2+1.2)/3.5 = 2.4/3.5 ≈ 0.6857
        result = _compute_overall_score(scores)
        assert abs(result - 0.6857) < 0.01

    def test_empty_scores(self):
        assert _compute_overall_score([]) == 0.0


class TestOverallSeverity:
    def test_worst_severity_wins(self):
        from scribeval.models.score import DimensionScore

        scores = [
            DimensionScore(
                dimension="omission",
                score=0.9,
                confidence=0.9,
                severity_summary=SeverityLevel.LOW,
                reasoning="r",
                rubric_version="1.0",
                judge_type="mock",
            ),
            DimensionScore(
                dimension="hallucination",
                score=0.5,
                confidence=0.9,
                severity_summary=SeverityLevel.HIGH,
                reasoning="r",
                rubric_version="1.0",
                judge_type="mock",
            ),
        ]
        assert _compute_overall_severity(scores) == SeverityLevel.HIGH


class TestPipeline:
    def test_evaluate_single_case(
        self, sample_case: EvaluationCase, rubrics_dir: Path
    ):
        mock = MockJudge()
        pipeline = EvaluationPipeline(
            dimensions=["omission", "hallucination"],
            judge=mock,
            rubric_dir=rubrics_dir,
        )
        report = pipeline.evaluate_case(sample_case)

        assert report.case_id == "test_gp_respiratory"
        assert report.scribe_product == "test_scribe"
        assert len(report.dimension_scores) == 2
        assert report.overall_score >= 0.0
        assert report.overall_score <= 1.0
        assert report.data_flow_disclosure
        assert report.scribeval_version == "0.1.0"

    def test_evaluate_all_dimensions(
        self, sample_case: EvaluationCase, rubrics_dir: Path
    ):
        mock = MockJudge()
        pipeline = EvaluationPipeline(judge=mock, rubric_dir=rubrics_dir)
        report = pipeline.evaluate_case(sample_case)

        assert len(report.dimension_scores) == 4
        dimensions = {ds.dimension for ds in report.dimension_scores}
        assert dimensions == {"omission", "hallucination", "medicolegal", "ahpra"}

    def test_evaluate_batch(
        self, sample_case: EvaluationCase, rubrics_dir: Path
    ):
        mock = MockJudge()
        pipeline = EvaluationPipeline(
            dimensions=["omission"],
            judge=mock,
            rubric_dir=rubrics_dir,
        )
        agg = pipeline.evaluate_batch([sample_case, sample_case])

        assert agg.case_count == 2
        assert "omission" in agg.dimension_statistics
        assert agg.dimension_statistics["omission"].mean == 0.75

    def test_data_flow_disclosure_mentions_model(
        self, sample_case: EvaluationCase, rubrics_dir: Path
    ):
        mock = MockJudge()
        pipeline = EvaluationPipeline(
            dimensions=["omission"],
            judge=mock,
            rubric_dir=rubrics_dir,
        )
        report = pipeline.evaluate_case(sample_case)
        assert "mock" in report.data_flow_disclosure.lower()

    def test_invalid_dimension_raises(self, rubrics_dir: Path):
        import pytest

        with pytest.raises(ValueError, match="Unknown dimension"):
            EvaluationPipeline(
                dimensions=["nonexistent"],
                judge=MockJudge(),
                rubric_dir=rubrics_dir,
            )
