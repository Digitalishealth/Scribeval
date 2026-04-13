"""Tests for reproducibility metadata and content hashing."""

from __future__ import annotations

from scribeval.reproducibility import ReproducibilityMetadata, content_hash


def test_content_hash_deterministic() -> None:
    a = content_hash("patient has a cough")
    b = content_hash("patient has a cough")
    assert a == b


def test_content_hash_differs_for_different_inputs() -> None:
    a = content_hash("patient has a cough")
    b = content_hash("patient has a fever")
    assert a != b


def test_content_hash_none_input() -> None:
    assert content_hash(None) == "none"


def test_content_hash_truncated_to_16_chars() -> None:
    assert len(content_hash("anything")) == 16


def test_reproducibility_metadata_serialises() -> None:
    meta = ReproducibilityMetadata(
        scribeval_version="0.1.0",
        judge_type="llm",
        judge_model="claude-sonnet-4-20250514",
        judge_temperature=0.0,
        judge_seed=None,
        transcript_hash=content_hash("transcript"),
        scribe_note_hash=content_hash("note"),
        reference_note_hash=None,
        rubric_hashes={"omission": content_hash("rubric")},
        dimensions=["omission"],
    )
    dumped = meta.model_dump()
    assert dumped["judge_temperature"] == 0.0
    assert dumped["rubric_hashes"]["omission"] == content_hash("rubric")
