"""Tests for the blinded comparison runner."""

from __future__ import annotations

import pytest

from scribeval.compare import NoteSubmission, ScribeSubmission, run_blinded_comparison
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
        NoteSubmission("ScribeA", "note A content for testing"),
        NoteSubmission("ScribeB", "note B content for testing"),
        NoteSubmission("ScribeC", "note C content for testing"),
    ]
    result = run_blinded_comparison(
        transcript_content=sample_transcript,
        submissions=submissions,
        pipeline=pipeline,
        rng_seed=1234,
    )
    assert set(result.label_to_product.keys()) == {"S1", "S2", "S3"}
    assert set(result.label_to_product.values()) == {"ScribeA", "ScribeB", "ScribeC"}
    assert result.label_to_submission == result.label_to_product
    assert len(result.per_label_reports) == 3


def test_compare_allows_five_submissions(sample_transcript: str) -> None:
    pipeline = _pipeline(MockJudge())
    submissions = [
        NoteSubmission(f"Scribe{idx}", f"note {idx}")
        for idx in range(1, 6)
    ]
    result = run_blinded_comparison(
        transcript_content=sample_transcript,
        submissions=submissions,
        pipeline=pipeline,
        rng_seed=42,
    )
    assert len(result.per_label_reports) == 5
    assert set(result.label_to_submission.values()) == {
        "Scribe1",
        "Scribe2",
        "Scribe3",
        "Scribe4",
        "Scribe5",
    }


def test_compare_rejects_more_than_five_submissions(sample_transcript: str) -> None:
    pipeline = _pipeline(MockJudge())
    submissions = [
        NoteSubmission(f"Scribe{idx}", f"note {idx}")
        for idx in range(1, 7)
    ]
    with pytest.raises(ValueError, match="At most 5 submissions"):
        run_blinded_comparison(
            transcript_content=sample_transcript,
            submissions=submissions,
            pipeline=pipeline,
        )


def test_compare_is_deterministic_with_seed(sample_transcript: str) -> None:
    pipeline = _pipeline(MockJudge())
    subs = [
        NoteSubmission("ScribeA", "A"),
        NoteSubmission("ScribeB", "B"),
        NoteSubmission("ScribeC", "C"),
    ]
    r1 = run_blinded_comparison(sample_transcript, subs, pipeline, rng_seed=7)
    r2 = run_blinded_comparison(sample_transcript, subs, pipeline, rng_seed=7)
    assert r1.label_to_product == r2.label_to_product


def test_compare_strips_product_name(sample_transcript: str) -> None:
    pipeline = _pipeline(MockJudge())
    result = run_blinded_comparison(
        sample_transcript,
        [
            NoteSubmission("ScribeA", "A"),
            NoteSubmission("ScribeB", "B"),
        ],
        pipeline=pipeline,
    )
    # Every blinded report should have scribe_product=None — the mapping
    # is only known through label_to_product.
    for report in result.per_label_reports.values():
        assert report.scribe_product is None
        assert report.candidate_label is None


def test_compare_keeps_legacy_scribe_submission(sample_transcript: str) -> None:
    pipeline = _pipeline(MockJudge())
    result = run_blinded_comparison(
        sample_transcript,
        [
            ScribeSubmission(product_name="ScribeA", scribe_note_content="A"),
            ScribeSubmission(product_name="gp", scribe_note_content="B"),
        ],
        pipeline=pipeline,
    )
    assert set(result.label_to_product.values()) == {"ScribeA", "gp"}
