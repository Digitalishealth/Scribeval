"""Blinded head-to-head comparison of multiple AI scribe outputs.

Compares N scribe outputs against the same consultation transcript. The
comparison is BLINDED: the judge never sees the scribe product name or
the order in which scribes were submitted. Scribes are assigned anonymous
labels (S1, S2, ...) in a randomised order before evaluation, and the
mapping from label back to real product is revealed only in the final
report.

This is the feature that matters most to a scribe vendor: it lets them
run their own product against competitors without the judge being biased
by brand recognition, and without being able to cherry-pick the
ordering. Blinding is enforced at the pipeline boundary so evaluators
cannot access the real product name even accidentally.
"""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from scribeval.models.case import (
    ConsultationType,
    EvaluationCase,
    ReferenceNote,
    ScribeNote,
    Transcript,
)
from scribeval.models.report import EvaluationReport
from scribeval.pipeline import EvaluationPipeline


@dataclass(frozen=True)
class ScribeSubmission:
    """A single scribe product's submission for a comparison run."""

    product_name: str
    scribe_note_content: str


class BlindedReport(BaseModel):
    """Result of a blinded comparison run.

    The `label_to_product` mapping is the unblinding key. It should be
    presented to the user only after the per-label scores are shown, so
    the visual order matches the score ranking and not the original
    submission order.
    """

    comparison_id: str
    transcript_hash: str
    label_to_product: dict[str, str]
    per_label_reports: dict[str, EvaluationReport]
    ranking: list[tuple[str, float]] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


def run_blinded_comparison(
    transcript_content: str,
    submissions: list[ScribeSubmission],
    pipeline: EvaluationPipeline,
    consultation_type: ConsultationType = ConsultationType.GP_STANDARD,
    reference_note_content: str | None = None,
    rng_seed: int | None = None,
) -> BlindedReport:
    """Run a blinded comparison across the given scribe submissions.

    The submissions are shuffled deterministically if `rng_seed` is set
    (important for reproducibility studies) and otherwise use a fresh
    random order per invocation. Each submission is wrapped in a case
    with `scribe_product=None` so the judge cannot see the brand.
    """
    if len(submissions) < 2:
        raise ValueError("At least two submissions are required for comparison.")

    rng = random.Random(rng_seed)
    shuffled = list(submissions)
    rng.shuffle(shuffled)

    label_to_product: dict[str, str] = {}
    per_label_reports: dict[str, EvaluationReport] = {}

    transcript = Transcript(content=transcript_content)
    reference = (
        ReferenceNote(content=reference_note_content)
        if reference_note_content
        else None
    )

    for idx, submission in enumerate(shuffled, start=1):
        label = f"S{idx}"
        label_to_product[label] = submission.product_name
        blinded_case = EvaluationCase(
            case_id=f"blinded_{label}",
            consultation_type=consultation_type,
            transcript=transcript,
            # Intentionally NO scribe_product — that is the whole point.
            scribe_note=ScribeNote(
                content=submission.scribe_note_content,
                scribe_product=None,
            ),
            reference_note=reference,
        )
        per_label_reports[label] = pipeline.evaluate_case(blinded_case)

    ranking = sorted(
        ((label, r.overall_score) for label, r in per_label_reports.items()),
        key=lambda x: x[1],
        reverse=True,
    )

    from scribeval.reproducibility import content_hash

    return BlindedReport(
        comparison_id=uuid.uuid4().hex[:12],
        transcript_hash=content_hash(transcript_content),
        label_to_product=label_to_product,
        per_label_reports=per_label_reports,
        ranking=ranking,
    )
