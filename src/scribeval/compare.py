"""Blinded head-to-head comparison of multiple final clinical notes.

Compares N candidate notes against the same consultation transcript. The
comparison is BLINDED: the judge never sees the submission label or
the order in which notes were submitted. Submissions are assigned anonymous
labels (S1, S2, ...) in a randomised order before evaluation, and the
mapping from blinded label back to the original submission label is revealed only in the final
report.

This supports AI-vs-AI comparison and AI-vs-GP baseline comparison with the
same scoring path: every final note is evaluated against the full transcript.
Blinding is enforced at the pipeline boundary so evaluators cannot access the
submission label even accidentally.
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
class NoteSubmission:
    """A single candidate final note for a comparison run."""

    label: str
    note_content: str

    @property
    def product_name(self) -> str:
        """Backward-compatible name used by older callers."""
        return self.label

    @property
    def scribe_note_content(self) -> str:
        """Backward-compatible note content name used by older callers."""
        return self.note_content


@dataclass(frozen=True)
class ScribeSubmission:
    """Backward-compatible AI-scribe submission shape.

    Prefer NoteSubmission for new code. This class remains so existing imports
    and keyword construction continue to work.
    """

    product_name: str
    scribe_note_content: str

    @property
    def label(self) -> str:
        return self.product_name

    @property
    def note_content(self) -> str:
        return self.scribe_note_content


class BlindedReport(BaseModel):
    """Result of a blinded comparison run.

    The `label_to_submission` mapping is the unblinding key. It should be
    presented to the user only after the per-label scores are shown, so
    the visual order matches the score ranking and not the original
    submission order.
    """

    comparison_id: str
    transcript_hash: str
    label_to_submission: dict[str, str] = Field(default_factory=dict)
    label_to_product: dict[str, str]
    per_label_reports: dict[str, EvaluationReport]
    ranking: list[tuple[str, float]] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


def run_blinded_comparison(
    transcript_content: str,
    submissions: list[NoteSubmission | ScribeSubmission],
    pipeline: EvaluationPipeline,
    consultation_type: ConsultationType = ConsultationType.GP_STANDARD,
    reference_note_content: str | None = None,
    rng_seed: int | None = None,
) -> BlindedReport:
    """Run a blinded comparison across the given final-note submissions.

    The submissions are shuffled deterministically if `rng_seed` is set
    (important for reproducibility studies) and otherwise use a fresh
    random order per invocation. Each submission is wrapped in a case
    with `scribe_product=None` so the judge cannot see the label.
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
        label_to_product[label] = submission.label
        blinded_case = EvaluationCase(
            case_id=f"blinded_{label}",
            consultation_type=consultation_type,
            transcript=transcript,
            # Intentionally NO scribe_product/candidate label — that is the whole point.
            scribe_note=ScribeNote(
                content=submission.note_content,
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
        label_to_submission=label_to_product,
        label_to_product=label_to_product,
        per_label_reports=per_label_reports,
        ranking=ranking,
    )
