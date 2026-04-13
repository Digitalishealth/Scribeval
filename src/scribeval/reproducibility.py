"""Reproducibility utilities: content hashing and provenance metadata.

Scribeval outputs should be reproducible. To support this, every evaluation
report records a set of hashes and version strings that together identify
exactly what inputs produced the report. Two reports with identical
reproducibility metadata should — modulo remote API non-determinism —
produce identical scores.

The hashes intentionally use SHA-256 truncated to 16 hex characters.
That is short enough to be human-readable in terminal output and long
enough that accidental collisions within a single evaluation run are
vanishingly unlikely. These hashes are not cryptographic commitments —
they exist so a reviewer can verify "this report was produced from
exactly these inputs" without needing the raw text.
"""

from __future__ import annotations

import hashlib

from pydantic import BaseModel


def content_hash(text: str) -> str:
    """Return a short deterministic hash of a string."""
    if text is None:
        return "none"
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


class ReproducibilityMetadata(BaseModel):
    """Provenance fields attached to every evaluation report.

    These fields let a reviewer verify what went into a report and
    re-run it deterministically if the underlying model is pinned.
    """

    scribeval_version: str
    judge_type: str
    judge_model: str | None = None
    judge_temperature: float | None = None
    judge_seed: int | None = None
    transcript_hash: str
    scribe_note_hash: str
    reference_note_hash: str | None = None
    rubric_hashes: dict[str, str]
    dimensions: list[str]
