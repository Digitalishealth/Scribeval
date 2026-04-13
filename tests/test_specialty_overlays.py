"""Tests for specialty-aware rubric overlays and pipeline consumption."""

from __future__ import annotations

from scribeval.pipeline import EvaluationPipeline
from scribeval.rubrics.loader import RubricSchema, ScoringConfig, SpecialtyOverlay
from tests.conftest import RUBRICS_DIR, MockJudge


def test_overlay_without_definition_returns_self() -> None:
    rubric = RubricSchema(
        dimension="omission",
        version="1.0",
        display_name="Omission",
        description="d",
        references=[],
        scoring=ScoringConfig(),
        severity_criteria={},
        evaluation_instructions="base instructions",
        australian_context="",
        specialty_overlays={},
    )
    assert rubric.for_specialty("ed_presentation") is rubric
    assert rubric.specialty_weight_multiplier("ed_presentation") == 1.0


def test_overlay_prepends_additional_criteria() -> None:
    rubric = RubricSchema(
        dimension="hallucination",
        version="1.0",
        display_name="H",
        description="d",
        references=[],
        scoring=ScoringConfig(),
        severity_criteria={},
        evaluation_instructions="base instructions",
        australian_context="",
        specialty_overlays={
            "ed_presentation": SpecialtyOverlay(
                weight_multiplier=1.3,
                additional_criteria="Extra ED criteria here",
            )
        },
    )
    applied = rubric.for_specialty("ed_presentation")
    assert applied is not rubric
    assert "Extra ED criteria here" in applied.evaluation_instructions
    assert "base instructions" in applied.evaluation_instructions
    assert rubric.specialty_weight_multiplier("ed_presentation") == 1.3


def test_pipeline_stores_specialty_multipliers_in_report(sample_case) -> None:
    pipeline = EvaluationPipeline(
        dimensions=["omission", "hallucination"],
        judge=MockJudge(),
        rubric_dir=RUBRICS_DIR,
    )
    report = pipeline.evaluate_case(sample_case)
    # Whatever the real rubric overlays define, the multipliers map must
    # have a float entry for every evaluated dimension.
    assert set(report.specialty_weight_multipliers.keys()) == {
        "omission",
        "hallucination",
    }
    for value in report.specialty_weight_multipliers.values():
        assert isinstance(value, float)
        assert value > 0
