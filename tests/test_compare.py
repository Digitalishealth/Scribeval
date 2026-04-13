"""Tests for the blinded comparison runner."""

from __future__ import annotations

import pytest

from scribeval.compare import ScribeSubmission, run_blinded_comparison
from scribeval.pipeline import EvaluationPipeline
from tests.conftest import RUBRICS_DIR, MockJudge


def _pipeline(judge: MockJudge) -> EvaluationPipeline:
    return EvaluationPipeline(
        dimensions=["omission", "hallucination"],
        judge=judge,
        rubric_dir=RUBRICS_DIR,
    )


def test_compare_requires_at_least_two(sample_transcript: str) -> None:
    pipeline = _pipeline(MockJudge())
    with pytest.raises(ValueError):
        run_blinded_comparison(
            transcript_content=sample_transcript,
            submissions=[ScribeSubmission("solo", "some note")],
            pipeline=pipeline,
        )


def test_compare_assigns_anonymous_labels(sample_transcript: str) -> None:
    pipeline = _pipeline(MockJudge())
    submissions = [
        ScribeSubmission("heidi", "note A content for testing"),
        ScribeSubmission("lyrebird", "note B content for testing"),
        ScribeSubmission("nabla", "note C content for testing"),
    ]
    result = run_blinded_comparison(
        transcript_content=sample_transcript,
        submissions=submissions,
        pipeline=pipeline,
        rng_seed=1234,
    )
    assert set(result.label_to_product.keys()) == {"S1", "S2", "S3"}
    assert set(result.label_to_product.values()) == {"heidi", "lyrebird", "nabla"}
    assert len(result.per_label_reports) == 3


def test_compare_is_deterministic_with_seed(sample_transcript: str) -> None:
    pipeline = _pipeline(MockJudge())
    subs = [
        ScribeSubmission("heidi", "A"),
        ScribeSubmission("lyrebird", "B"),
        ScribeSubmission("nabla", "C"),
    ]
    r1 = run_blinded_comparison(sample_transcript, subs, pipeline, rng_seed=7)
    r2 = run_blinded_comparison(sample_transcript, subs, pipeline, rng_seed=7)
    assert r1.label_to_product == r2.label_to_product


def test_compare_strips_product_name(sample_transcript: str) -> None:
    pipeline = _pipeline(MockJudge())
    result = run_blinded_comparison(
        sample_transcript,
        [
            ScribeSubmission("heidi", "A"),
            ScribeSubmission("lyrebird", "B"),
        ],
        pipeline=pipeline,
    )
    # Every blinded report should have scribe_product=None — the mapping
    # is only known through label_to_product.
    for report in result.per_label_reports.values():
        assert report.scribe_product is None
