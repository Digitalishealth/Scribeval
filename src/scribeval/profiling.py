"""Cost and latency profiling for evaluation runs.

Lets users see how many tokens and wall-seconds an evaluation consumed,
and (roughly) how much that would have cost at published API prices.
This defends against the "Scribeval is slow and expensive, we can't
afford to run it regularly" critique by making the cost legible.

What is measured:
- Wall-clock latency per evaluator (single run) and total
- Prompt token count estimate (via len(prompt) / 4 as a conservative
  heuristic, since we do not always have direct access to tokenizer
  output without re-running tiktoken-style tooling)
- Response token count estimate (same heuristic)
- Dollar cost at the user-supplied rate per million tokens

This module deliberately makes NO live network calls and has NO
dependency on the judge's API surface. It is a wrapper that instruments
any BaseJudge by recording timings around `evaluate()`.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from scribeval.judges.base import BaseJudge

# Public pricing snapshot for indicative cost reporting. These are NOT
# live pricing — they are a sensible default that users can override via
# the CLI. Prices are USD per million tokens.
DEFAULT_PRICING: dict[str, tuple[float, float]] = {
    # model: (input_usd_per_mtok, output_usd_per_mtok)
    "claude-sonnet-4-20250514": (3.00, 15.00),
    "claude-opus-4-20250514": (15.00, 75.00),
    "claude-haiku-4-5-20251001": (0.80, 4.00),
}


def estimate_tokens(text: str) -> int:
    """Conservative token-count heuristic: 1 token per ~4 characters.

    This is deliberately a rough heuristic — we favour being independent
    of any tokenizer vendor over exact counts. Users who need exact
    counts should run `anthropic.count_tokens()` separately.
    """
    if not text:
        return 0
    return max(1, len(text) // 4)


@dataclass
class CallProfile:
    """Profile of a single judge call."""

    label: str
    duration_s: float
    prompt_tokens: int
    response_tokens: int
    cost_usd: float


@dataclass
class ProfileReport:
    """Aggregate profile across all calls made during an evaluation."""

    judge_model: str | None
    input_rate_per_mtok: float
    output_rate_per_mtok: float
    calls: list[CallProfile] = field(default_factory=list)

    @property
    def total_duration_s(self) -> float:
        return round(sum(c.duration_s for c in self.calls), 3)

    @property
    def total_prompt_tokens(self) -> int:
        return sum(c.prompt_tokens for c in self.calls)

    @property
    def total_response_tokens(self) -> int:
        return sum(c.response_tokens for c in self.calls)

    @property
    def total_cost_usd(self) -> float:
        return round(sum(c.cost_usd for c in self.calls), 6)

    def as_dict(self) -> dict:
        return {
            "judge_model": self.judge_model,
            "input_rate_per_mtok": self.input_rate_per_mtok,
            "output_rate_per_mtok": self.output_rate_per_mtok,
            "n_calls": len(self.calls),
            "total_duration_s": self.total_duration_s,
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_response_tokens": self.total_response_tokens,
            "total_cost_usd": self.total_cost_usd,
            "calls": [
                {
                    "label": c.label,
                    "duration_s": round(c.duration_s, 3),
                    "prompt_tokens": c.prompt_tokens,
                    "response_tokens": c.response_tokens,
                    "cost_usd": round(c.cost_usd, 6),
                }
                for c in self.calls
            ],
        }

    def format_summary(self) -> str:
        """Human-readable one-paragraph summary of cost and latency."""
        lines = [
            f"Judge: {self.judge_model or 'unknown'}",
            f"Calls: {len(self.calls)}",
            f"Wall time: {self.total_duration_s}s",
            f"Tokens (in/out): {self.total_prompt_tokens} / {self.total_response_tokens}",
            f"Estimated cost: USD ${self.total_cost_usd:.4f}",
        ]
        return " | ".join(lines)


class ProfilingJudge(BaseJudge):
    """Wraps any BaseJudge to record per-call timings and token counts.

    Decorator pattern — any evaluator that accepts a BaseJudge will
    accept this wrapper without modification, so instrumenting a
    pipeline for profiling is a one-line change.
    """

    def __init__(
        self,
        inner: BaseJudge,
        input_rate_per_mtok: float | None = None,
        output_rate_per_mtok: float | None = None,
    ):
        self._inner = inner
        default_in, default_out = _default_rates_for(inner.judge_model)
        self._input_rate = (
            input_rate_per_mtok if input_rate_per_mtok is not None else default_in
        )
        self._output_rate = (
            output_rate_per_mtok if output_rate_per_mtok is not None else default_out
        )
        self.report = ProfileReport(
            judge_model=inner.judge_model,
            input_rate_per_mtok=self._input_rate,
            output_rate_per_mtok=self._output_rate,
        )
        self._next_label: str | None = None

    @property
    def judge_type(self) -> str:
        return self._inner.judge_type

    @property
    def judge_model(self) -> str:
        return self._inner.judge_model

    @property
    def inner(self) -> BaseJudge:
        return self._inner

    def label_next_call(self, label: str) -> None:
        """Tag the NEXT evaluate() call with a label (usually the dimension).

        Not thread-safe — scribeval evaluates dimensions sequentially so
        this simple one-shot label is sufficient for reporting.
        """
        self._next_label = label

    def evaluate(self, prompt: str) -> str:
        label = self._next_label or "unlabelled"
        self._next_label = None
        start = time.perf_counter()
        response = self._inner.evaluate(prompt)
        duration = time.perf_counter() - start

        prompt_tokens = estimate_tokens(prompt)
        response_tokens = estimate_tokens(response)
        cost = (
            prompt_tokens * self._input_rate / 1_000_000
            + response_tokens * self._output_rate / 1_000_000
        )

        self.report.calls.append(
            CallProfile(
                label=label,
                duration_s=duration,
                prompt_tokens=prompt_tokens,
                response_tokens=response_tokens,
                cost_usd=cost,
            )
        )
        return response


def _default_rates_for(model: str | None) -> tuple[float, float]:
    """Look up default rates for a model name; fall back to zero."""
    if not model:
        return 0.0, 0.0
    for key, rates in DEFAULT_PRICING.items():
        if key in model:
            return rates
    return 0.0, 0.0
