"""Human-rater judge: interactive TTY questionnaire for clinician scoring.

Used for:
1. Running inter-rater reliability studies against the LLM judge.
2. Scoring notes locally without transmitting data to any external API.
3. Collecting gold-standard human ratings for the calibration workflow.

The judge implements the same BaseJudge interface as LLMJudge, so any
evaluator (omission, hallucination, PDQI-9, etc.) can be driven by a
human rater without modification. The rater sees the full prompt that
the LLM would see, so the question being asked is transparent.

UX notes:
- Default to non-interactive failure if stdin is not a TTY, to prevent
  accidental blocking in CI or batch runs.
- Allow a `canned_response` override for tests and scripted demos.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable

from scribeval.judges.base import BaseJudge
from scribeval.models.score import SeverityLevel

SEVERITY_LABELS: list[str] = [s.value for s in SeverityLevel]

_PROMPT_FOOTER = """
-------------------------------------------------------------
HUMAN RATER: please review the prompt above and respond below.
-------------------------------------------------------------
"""


class HumanJudge(BaseJudge):
    """Interactive TTY judge for human raters.

    Each call prints the full evaluation prompt, then walks the rater
    through a short structured questionnaire (score, confidence,
    severity, reasoning, optional findings). The output is formatted
    as the same JSON schema that LLMJudge produces.
    """

    def __init__(
        self,
        rater_name: str = "anonymous",
        input_fn: Callable[[str], str] | None = None,
        output_fn: Callable[[str], None] | None = None,
        require_tty: bool = True,
        canned_response: dict | None = None,
    ):
        self._rater = rater_name
        self._input = input_fn or input
        self._output = output_fn or (lambda s: print(s))
        self._require_tty = require_tty
        self._canned = canned_response

    @property
    def judge_type(self) -> str:
        return "human"

    @property
    def judge_model(self) -> str:
        return f"human:{self._rater}"

    def evaluate(self, prompt: str) -> str:
        if self._canned is not None:
            return json.dumps(self._canned)

        if self._require_tty and not sys.stdin.isatty():
            raise RuntimeError(
                "HumanJudge requires an interactive TTY. Pass canned_response "
                "for non-interactive use, or run from a terminal."
            )

        self._output("\n" + "=" * 60)
        self._output(prompt)
        self._output(_PROMPT_FOOTER)

        score = _read_float(
            self._input, "Score (0.0-1.0, 1.0 = perfect): ", 0.0, 1.0
        )
        confidence = _read_float(
            self._input, "Your confidence in this rating (0.0-1.0): ", 0.0, 1.0
        )
        severity = _read_choice(
            self._input,
            f"Severity summary {SEVERITY_LABELS}: ",
            SEVERITY_LABELS,
        )
        reasoning = self._input("Reasoning (one line): ").strip() or "(none provided)"

        findings: list[dict] = []
        n_findings = _read_int(self._input, "Number of findings to record: ", 0, 20)
        for i in range(n_findings):
            self._output(f"\n  Finding {i + 1}:")
            description = self._input("    Description: ").strip()
            f_sev = _read_choice(
                self._input, f"    Severity {SEVERITY_LABELS}: ", SEVERITY_LABELS
            )
            clinical_impact = self._input("    Clinical impact (or blank): ").strip()
            findings.append(
                {
                    "description": description,
                    "severity": f_sev,
                    "clinical_impact": clinical_impact or None,
                    "transcript_excerpt": None,
                    "note_excerpt": None,
                }
            )

        return json.dumps(
            {
                "score": score,
                "confidence": confidence,
                "severity_summary": severity,
                "reasoning": f"[human:{self._rater}] {reasoning}",
                "findings": findings,
            }
        )


# --------------------------------------------------------------------------- #
# Input helpers
# --------------------------------------------------------------------------- #


def _read_float(
    input_fn: Callable[[str], str], prompt: str, lo: float, hi: float
) -> float:
    while True:
        raw = input_fn(prompt).strip()
        try:
            value = float(raw)
        except ValueError:
            print(f"  Not a number: '{raw}'")
            continue
        if value < lo or value > hi:
            print(f"  Out of range [{lo}, {hi}]: {value}")
            continue
        return value


def _read_int(
    input_fn: Callable[[str], str], prompt: str, lo: int, hi: int
) -> int:
    while True:
        raw = input_fn(prompt).strip()
        if not raw:
            return lo
        try:
            value = int(raw)
        except ValueError:
            print(f"  Not an integer: '{raw}'")
            continue
        if value < lo or value > hi:
            print(f"  Out of range [{lo}, {hi}]: {value}")
            continue
        return value


def _read_choice(
    input_fn: Callable[[str], str], prompt: str, choices: list[str]
) -> str:
    while True:
        raw = input_fn(prompt).strip().lower()
        if raw in choices:
            return raw
        print(f"  Invalid choice. Must be one of {choices}")
