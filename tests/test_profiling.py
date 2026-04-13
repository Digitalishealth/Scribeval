"""Tests for the ProfilingJudge wrapper."""

from __future__ import annotations

from scribeval.profiling import ProfilingJudge, estimate_tokens
from tests.conftest import MockJudge


def test_estimate_tokens_nonzero_for_nonempty() -> None:
    assert estimate_tokens("") == 0
    assert estimate_tokens("hello world") > 0


def test_profiling_judge_records_calls() -> None:
    judge = ProfilingJudge(MockJudge())
    judge.evaluate("prompt one" * 50)
    judge.evaluate("prompt two" * 50)
    assert len(judge.report.calls) == 2
    assert judge.report.total_prompt_tokens > 0
    assert judge.report.total_duration_s >= 0.0


def test_profiling_judge_labels_next_call() -> None:
    judge = ProfilingJudge(MockJudge())
    judge.label_next_call("omission")
    judge.evaluate("some prompt")
    judge.evaluate("another prompt")
    assert judge.report.calls[0].label == "omission"
    # Label is one-shot — the second call should revert to the default
    assert judge.report.calls[1].label == "unlabelled"


def test_profiling_judge_cost_uses_configured_rates() -> None:
    judge = ProfilingJudge(
        MockJudge(),
        input_rate_per_mtok=3.0,
        output_rate_per_mtok=15.0,
    )
    judge.evaluate("prompt")
    report_dict = judge.report.as_dict()
    assert report_dict["input_rate_per_mtok"] == 3.0
    assert report_dict["output_rate_per_mtok"] == 15.0


def test_profile_summary_contains_key_fields() -> None:
    judge = ProfilingJudge(MockJudge())
    judge.evaluate("prompt")
    summary = judge.report.format_summary()
    assert "Calls:" in summary
    assert "Wall time" in summary
