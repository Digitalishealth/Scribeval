"""Evaluation input models: consultation transcripts, candidate notes, and references."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ConsultationType(StrEnum):
    """Australian clinical consultation types."""

    GP_STANDARD = "gp_standard"
    GP_LONG = "gp_long"
    GP_TELEHEALTH = "gp_telehealth"
    ED_PRESENTATION = "ed_presentation"
    SPECIALIST_REVIEW = "specialist_review"
    PSYCHIATRY = "psychiatry"
    PAEDIATRICS = "paediatrics"
    ALLIED_HEALTH = "allied_health"


class Transcript(BaseModel):
    """Raw consultation transcript."""

    content: str = Field(min_length=1)
    source_format: str = "text"
    duration_seconds: int | None = None
    speaker_labels: bool = False


class ScribeNote(BaseModel):
    """The candidate final note to be evaluated.

    The class name is retained for backward compatibility with older API users.
    """

    content: str = Field(min_length=1)
    scribe_product: str | None = None
    scribe_version: str | None = None
    generation_timestamp: datetime | None = None


class ReferenceNote(BaseModel):
    """Gold-standard clinician-authored reference note (optional)."""

    content: str = Field(min_length=1)
    author_role: str = "GP"
    review_status: str = "unreviewed"


class EvaluationCase(BaseModel):
    """A single evaluation case representing one consultation."""

    case_id: str = Field(min_length=1)
    consultation_type: ConsultationType
    transcript: Transcript
    scribe_note: ScribeNote
    reference_note: ReferenceNote | None = None
    metadata: dict = Field(default_factory=dict)
