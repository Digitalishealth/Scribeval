"""Shared test fixtures for Scribeval."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scribeval.judges.base import BaseJudge
from scribeval.models.case import (
    ConsultationType,
    EvaluationCase,
    ReferenceNote,
    ScribeNote,
    Transcript,
)

SAMPLES_DIR = Path(__file__).parent.parent / "samples"
RUBRICS_DIR = Path(__file__).parent.parent / "rubrics"


class MockJudge(BaseJudge):
    """A mock judge that returns configurable canned responses."""

    def __init__(self, response: dict | None = None):
        self._response = response or {
            "score": 0.75,
            "confidence": 0.85,
            "severity_summary": "moderate",
            "reasoning": "Mock evaluation reasoning for testing purposes.",
            "findings": [
                {
                    "description": "Mock finding for testing",
                    "severity": "moderate",
                    "transcript_excerpt": "relevant transcript text",
                    "note_excerpt": "relevant note text",
                    "clinical_impact": "Moderate clinical impact for testing",
                }
            ],
        }

    @property
    def judge_type(self) -> str:
        return "mock"

    @property
    def judge_model(self) -> str | None:
        return None

    def evaluate(self, prompt: str) -> str:
        return json.dumps(self._response)


@pytest.fixture
def mock_judge() -> MockJudge:
    """A mock judge returning a default moderate-severity response."""
    return MockJudge()


@pytest.fixture
def perfect_mock_judge() -> MockJudge:
    """A mock judge returning a perfect score with no findings."""
    return MockJudge(
        response={
            "score": 1.0,
            "confidence": 0.95,
            "severity_summary": "none",
            "reasoning": "No issues found. The scribe output accurately captures the consultation.",
            "findings": [],
        }
    )


@pytest.fixture
def sample_transcript() -> str:
    """Load the GP respiratory sample transcript."""
    return (SAMPLES_DIR / "case_gp_respiratory" / "transcript.txt").read_text()


@pytest.fixture
def sample_scribe_note() -> str:
    """Load the GP respiratory sample scribe output."""
    return (SAMPLES_DIR / "case_gp_respiratory" / "scribe_output.txt").read_text()


@pytest.fixture
def sample_reference_note() -> str:
    """Load the GP respiratory sample reference note."""
    return (SAMPLES_DIR / "case_gp_respiratory" / "reference_note.txt").read_text()


@pytest.fixture
def sample_case(
    sample_transcript: str, sample_scribe_note: str, sample_reference_note: str
) -> EvaluationCase:
    """A complete evaluation case from sample data."""
    return EvaluationCase(
        case_id="test_gp_respiratory",
        consultation_type=ConsultationType.GP_STANDARD,
        transcript=Transcript(content=sample_transcript),
        scribe_note=ScribeNote(
            content=sample_scribe_note,
            scribe_product="test_scribe",
        ),
        reference_note=ReferenceNote(content=sample_reference_note),
    )


@pytest.fixture
def sample_case_no_reference(
    sample_transcript: str, sample_scribe_note: str
) -> EvaluationCase:
    """An evaluation case without a reference note."""
    return EvaluationCase(
        case_id="test_gp_respiratory_no_ref",
        consultation_type=ConsultationType.GP_STANDARD,
        transcript=Transcript(content=sample_transcript),
        scribe_note=ScribeNote(content=sample_scribe_note),
    )


@pytest.fixture
def rubrics_dir() -> Path:
    """Path to the rubrics directory."""
    return RUBRICS_DIR
