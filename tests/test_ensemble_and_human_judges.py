"""Tests for the ensemble and human judges."""

from __future__ import annotations

import json

import pytest

from scribeval.judges.ensemble import EnsembleJudge
from scribeval.judges.human import HumanJudge
from tests.conftest import MockJudge


def test_ensemble_requires_at_least_one_judge() -> None:
    with pytest.raises(ValueError):
        EnsembleJudge([])


def test_ensemble_single_judge_passes_through() -> None:
    inner = MockJudge()
    ensemble = EnsembleJudge([inner])
    out = ensemble.evaluate("irrelevant prompt")
    parsed = json.loads(out)
    assert parsed["score"] == 0.75
    # Reasoning is re-formatted with [Judge N] attribution and the
    # ensemble meta-line, so it is no longer exactly equal to the original.
    assert "[Judge 1]" in parsed["reasoning"]
    assert "[Ensemble]" in parsed["reasoning"]


def test_ensemble_averages_scores() -> None:
    judge_a = MockJudge(
        {
            "score": 0.8,
            "confidence": 0.9,
            "severity_summary": "low",
            "reasoning": "a",
            "findings": [],
        }
    )
    judge_b = MockJudge(
        {
            "score": 0.6,
            "confidence": 0.9,
            "severity_summary": "moderate",
            "reasoning": "b",
            "findings": [],
        }
    )
    ensemble = EnsembleJudge([judge_a, judge_b])
    parsed = json.loads(ensemble.evaluate("prompt"))
    assert parsed["score"] == pytest.approx(0.7, abs=1e-4)
    # Worst severity kept
    assert parsed["severity_summary"] == "moderate"


def test_ensemble_disagreement_reduces_confidence() -> None:
    agree_a = MockJudge(
        {"score": 0.8, "confidence": 0.9, "severity_summary": "none",
         "reasoning": "", "findings": []}
    )
    agree_b = MockJudge(
        {"score": 0.8, "confidence": 0.9, "severity_summary": "none",
         "reasoning": "", "findings": []}
    )
    disagree_a = MockJudge(
        {"score": 0.2, "confidence": 0.9, "severity_summary": "none",
         "reasoning": "", "findings": []}
    )
    disagree_b = MockJudge(
        {"score": 0.9, "confidence": 0.9, "severity_summary": "none",
         "reasoning": "", "findings": []}
    )
    agree = json.loads(EnsembleJudge([agree_a, agree_b]).evaluate("p"))
    disagree = json.loads(EnsembleJudge([disagree_a, disagree_b]).evaluate("p"))
    assert agree["confidence"] > disagree["confidence"]


def test_ensemble_dedupes_findings() -> None:
    a = MockJudge(
        {
            "score": 0.5,
            "confidence": 0.8,
            "severity_summary": "moderate",
            "reasoning": "",
            "findings": [
                {"description": "Missing allergy", "severity": "critical"},
                {"description": "Wrong dose", "severity": "high"},
            ],
        }
    )
    b = MockJudge(
        {
            "score": 0.5,
            "confidence": 0.8,
            "severity_summary": "moderate",
            "reasoning": "",
            "findings": [
                {"description": "Missing allergy", "severity": "critical"},
                {"description": "Fabricated finding", "severity": "high"},
            ],
        }
    )
    parsed = json.loads(EnsembleJudge([a, b]).evaluate("p"))
    descs = {f["description"] for f in parsed["findings"]}
    assert descs == {"Missing allergy", "Wrong dose", "Fabricated finding"}


def test_human_judge_canned_response() -> None:
    canned = {
        "score": 0.9,
        "confidence": 0.8,
        "severity_summary": "low",
        "reasoning": "Clinician review",
        "findings": [],
    }
    judge = HumanJudge(canned_response=canned)
    out = json.loads(judge.evaluate("prompt"))
    assert out["score"] == 0.9
    assert out["severity_summary"] == "low"


def test_human_judge_refuses_non_tty_without_canned() -> None:
    judge = HumanJudge(require_tty=True)
    with pytest.raises(RuntimeError):
        judge.evaluate("prompt")


def test_human_judge_interactive_via_callable(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = iter([
        "0.8",          # score
        "0.9",          # confidence
        "low",          # severity
        "Looks fine",   # reasoning
        "0",            # number of findings
    ])
    out: list[str] = []
    judge = HumanJudge(
        rater_name="dr_test",
        input_fn=lambda _prompt: next(responses),
        output_fn=out.append,
        require_tty=False,
    )
    parsed = json.loads(judge.evaluate("prompt"))
    assert parsed["score"] == 0.8
    assert parsed["reasoning"].startswith("[human:dr_test]")
