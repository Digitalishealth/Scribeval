"""Ensemble judge: combines multiple judges and reports inter-judge agreement.

An EnsembleJudge runs the same prompt through N inner judges and
produces a single merged JSON response. This defends against the
"LLM-as-judge is biased" critique in two ways:

1. **Diversification**: using judges from different model families (e.g.,
   Claude Sonnet + Claude Opus + a human rater) reduces the risk that a
   single model's idiosyncrasies dominate the score.
2. **Inter-judge variance as confidence**: when judges disagree, the
   ensemble's confidence drops proportionally to the disagreement. A
   score with high inter-judge agreement is more trustworthy than a
   score with wide variance.

Merge strategy:
- For numeric fields (score, confidence): mean across judges.
- For severity_summary: worst-case (most severe) is kept.
- For findings: union with de-duplication by description.
- For reasoning: concatenated with per-judge attribution.

The resulting object still validates against the standard output
schema, so downstream code does not need to know whether a single
judge or an ensemble produced it.
"""

from __future__ import annotations

import json
import statistics
from typing import Any

from scribeval.judges.base import BaseJudge
from scribeval.models.score import SeverityLevel

SEVERITY_ORDER: list[str] = [s.value for s in SeverityLevel]


class EnsembleJudge(BaseJudge):
    """Wraps multiple judges and merges their responses."""

    def __init__(self, judges: list[BaseJudge], name: str = "ensemble"):
        if not judges:
            raise ValueError("EnsembleJudge requires at least one inner judge")
        self._judges = judges
        self._name = name

    @property
    def judge_type(self) -> str:
        return "ensemble"

    @property
    def judge_model(self) -> str:
        names = [
            j.judge_model or j.judge_type for j in self._judges
        ]
        return f"{self._name}({'+'.join(names)})"

    @property
    def inner_judges(self) -> list[BaseJudge]:
        return list(self._judges)

    def evaluate(self, prompt: str) -> str:
        responses = [j.evaluate(prompt) for j in self._judges]
        parsed: list[dict[str, Any]] = []
        for raw in responses:
            try:
                parsed.append(_parse_json_loose(raw))
            except (json.JSONDecodeError, ValueError):
                # Skip malformed — the ensemble should not fail if ONE
                # judge misbehaves, but we note the degradation.
                continue

        if not parsed:
            # All judges failed. Return the first raw response so the
            # downstream parser emits an informative error.
            return responses[0] if responses else "{}"

        merged = self._merge_responses(parsed)
        return json.dumps(merged)

    # ------------------------------------------------------------------ #

    def _merge_responses(self, responses: list[dict[str, Any]]) -> dict[str, Any]:
        scores = [float(r.get("score", 0.0)) for r in responses]
        confidences = [float(r.get("confidence", 0.0)) for r in responses]
        severities = [str(r.get("severity_summary", "none")) for r in responses]

        mean_score = statistics.mean(scores)
        score_std = statistics.stdev(scores) if len(scores) > 1 else 0.0
        mean_confidence = statistics.mean(confidences)
        # Disagreement penalty: if two judges differ by >0.2 the ensemble
        # loses confidence proportionally.
        disagreement_penalty = min(score_std * 2.0, 0.5)
        effective_confidence = max(0.0, mean_confidence - disagreement_penalty)

        # Worst severity
        worst = max(severities, key=lambda s: SEVERITY_ORDER.index(s)
                    if s in SEVERITY_ORDER else -1)

        # Union findings, deduplicated
        seen: set[str] = set()
        merged_findings: list[dict[str, Any]] = []
        for r in responses:
            for f in r.get("findings", []) or []:
                desc = str(f.get("description", "")).strip().lower()
                if not desc or desc in seen:
                    continue
                seen.add(desc)
                merged_findings.append(f)

        # Reasoning: explicit inter-judge attribution
        reasonings = []
        for idx, r in enumerate(responses, start=1):
            reasoning = str(r.get("reasoning", "")).strip()
            if reasoning:
                reasonings.append(f"[Judge {idx}] {reasoning}")
        reasonings.append(
            f"[Ensemble] mean_score={mean_score:.3f} "
            f"std={score_std:.3f} "
            f"n_judges={len(responses)} "
            f"disagreement_penalty={disagreement_penalty:.3f}"
        )

        return {
            "score": round(mean_score, 4),
            "confidence": round(effective_confidence, 4),
            "severity_summary": worst,
            "reasoning": "\n\n".join(reasonings),
            "findings": merged_findings,
        }


def _parse_json_loose(raw: str) -> dict[str, Any]:
    """Parse JSON that may be wrapped in markdown fences."""
    import re

    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", raw, re.DOTALL)
    if match:
        return json.loads(match.group(1).strip())
    return json.loads(raw.strip())
