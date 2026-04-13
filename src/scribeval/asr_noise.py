"""Simulate the mess of real ASR transcripts in synthetic test data.

Clean synthetic transcripts are unrealistic. Real AI-scribe input is
disfluent: partial words, dropped endings, homophone substitutions,
speaker misattribution, hesitation markers, crosstalk, background noise.
A scribe that aces a clean transcript may fall apart on a transcript
that contains "the patient is taking amox- amoxy uh amoxicillin five
hundred uh milligrams tee dee ess".

This module injects deterministic (seeded) ASR-style noise into a clean
transcript so evaluators can measure robustness. It is NOT a real
acoustic model; it uses surface substitutions that plausibly mirror
common ASR failures on Australian clinical speech.

Noise categories (all seed-deterministic):
- `homophone`: substitute medical homophones (e.g., ilium/ileum, dysuria
  misheard as "this area")
- `mumble`: mark occasional words with `[inaudible]`
- `filler`: sprinkle "uh", "um", "you know" into the speaker turns
- `partial`: truncate a word midway ("amox- amoxicillin")
- `speaker_swap`: swap speaker labels on a small fraction of turns
- `crosstalk`: merge two adjacent turns into one with `[crosstalk]`
- `background`: inject `[background noise]` markers

The intensity parameter (0.0-1.0) controls how aggressively noise is
applied. `intensity=0.0` is a no-op.

Usage::

    dirty = apply_asr_noise(clean_text, intensity=0.3, seed=1234)
    case.transcript.content = dirty

Why this matters for critique defence:
- Scribe vendors claim their systems tolerate noisy ASR. Scribeval can
  quantify that claim by scoring the same scribe on clean vs noisy
  versions of the same transcript and reporting the delta.
- If a scribe's hallucination score drops by 0.3 under 20% noise, that
  is a real product risk that a clean-transcript benchmark hides.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from enum import StrEnum


class NoiseType(StrEnum):
    HOMOPHONE = "homophone"
    MUMBLE = "mumble"
    FILLER = "filler"
    PARTIAL = "partial"
    SPEAKER_SWAP = "speaker_swap"
    CROSSTALK = "crosstalk"
    BACKGROUND = "background"


# Medical homophone substitutions. Each tuple is (pattern, replacement).
# These are chosen to be errors a real ASR system makes on Australian
# clinical speech — not random noise. Clinically plausible mis-hearings
# are what cause scribe errors.
MEDICAL_HOMOPHONES: list[tuple[str, str]] = [
    (r"\bdysuria\b", "this area"),
    (r"\bileum\b", "ilium"),
    (r"\bilium\b", "ileum"),
    (r"\bapnea\b", "a near"),
    (r"\bdysphagia\b", "dysphasia"),
    (r"\bdysphasia\b", "dysphagia"),
    (r"\bhypertension\b", "hypotension"),
    (r"\bhypotension\b", "hypertension"),
    (r"\bhyperkalaemia\b", "hypokalaemia"),
    (r"\bhypokalaemia\b", "hyperkalaemia"),
    (r"\bperoneal\b", "perineal"),
    (r"\bperineal\b", "peroneal"),
    (r"\bomeprazole\b", "omeprazole"),  # often misheard but spelling is stable
    (r"\bdischarge\b", "discharge"),
    (r"\bTDS\b", "TDS"),
    (r"\bmgs?\b", "mg"),
]

FILLERS: list[str] = ["uh", "um", "you know", "like", "sort of", "ah"]


@dataclass
class NoiseReport:
    """Summary of noise injected into a transcript."""

    intensity: float
    total_edits: int
    edits_by_type: dict[str, int]


def apply_asr_noise(
    transcript: str,
    intensity: float = 0.2,
    seed: int | None = None,
    types: list[NoiseType] | None = None,
) -> tuple[str, NoiseReport]:
    """Apply seeded ASR-style noise to a transcript string.

    Parameters:
    - intensity: 0.0 (no-op) to 1.0 (heavy). Controls fraction of tokens
      and turns that receive noise.
    - seed: RNG seed for reproducibility.
    - types: subset of noise types to apply; defaults to all.

    Returns the modified transcript and a NoiseReport.
    """
    if intensity <= 0.0:
        return transcript, NoiseReport(intensity=0.0, total_edits=0, edits_by_type={})
    if intensity > 1.0:
        intensity = 1.0

    rng = random.Random(seed)
    active = set(types or list(NoiseType))
    edits: dict[str, int] = {t.value: 0 for t in NoiseType}

    text = transcript

    if NoiseType.HOMOPHONE in active:
        text, n = _apply_homophones(text, intensity, rng)
        edits[NoiseType.HOMOPHONE.value] += n

    # Speaker-label operations act on line-structured transcripts.
    lines = text.splitlines()
    if NoiseType.SPEAKER_SWAP in active:
        lines, n = _apply_speaker_swap(lines, intensity, rng)
        edits[NoiseType.SPEAKER_SWAP.value] += n
    if NoiseType.CROSSTALK in active:
        lines, n = _apply_crosstalk(lines, intensity, rng)
        edits[NoiseType.CROSSTALK.value] += n

    text = "\n".join(lines)

    if NoiseType.FILLER in active:
        text, n = _apply_fillers(text, intensity, rng)
        edits[NoiseType.FILLER.value] += n
    if NoiseType.PARTIAL in active:
        text, n = _apply_partials(text, intensity, rng)
        edits[NoiseType.PARTIAL.value] += n
    if NoiseType.MUMBLE in active:
        text, n = _apply_mumble(text, intensity, rng)
        edits[NoiseType.MUMBLE.value] += n
    if NoiseType.BACKGROUND in active:
        text, n = _apply_background(text, intensity, rng)
        edits[NoiseType.BACKGROUND.value] += n

    total = sum(edits.values())
    return text, NoiseReport(
        intensity=intensity,
        total_edits=total,
        edits_by_type={k: v for k, v in edits.items() if v > 0},
    )


# --------------------------------------------------------------------------- #
# Per-category injection
# --------------------------------------------------------------------------- #


def _apply_homophones(text: str, intensity: float, rng: random.Random) -> tuple[str, int]:
    """Substitute medical homophones at a rate proportional to intensity."""
    n = 0
    for pattern, replacement in MEDICAL_HOMOPHONES:
        # For each match, flip a coin weighted by intensity. The closure
        # binds `replacement` via a default argument to avoid the late-
        # binding trap in Python's for-loop scoping (ruff B023).
        def repl(
            match: re.Match[str],
            _replacement: str = replacement,
        ) -> str:
            nonlocal n
            if rng.random() < intensity * 0.6:  # homophones are relatively rare
                n += 1
                return _replacement
            return match.group(0)

        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
    return text, n


def _apply_fillers(text: str, intensity: float, rng: random.Random) -> tuple[str, int]:
    """Insert hesitation fillers between words at a rate proportional to intensity."""
    tokens = text.split(" ")
    out: list[str] = []
    n = 0
    for tok in tokens:
        out.append(tok)
        if rng.random() < intensity * 0.08:
            out.append(rng.choice(FILLERS))
            n += 1
    return " ".join(out), n


def _apply_partials(text: str, intensity: float, rng: random.Random) -> tuple[str, int]:
    """Mark a word with a partial-word stutter ("amox- amoxicillin")."""
    tokens = text.split(" ")
    n = 0
    for i, tok in enumerate(tokens):
        if rng.random() < intensity * 0.03 and len(tok) >= 6 and tok.isalpha():
            prefix_len = max(3, len(tok) // 2)
            tokens[i] = f"{tok[:prefix_len]}- {tok}"
            n += 1
    return " ".join(tokens), n


def _apply_mumble(text: str, intensity: float, rng: random.Random) -> tuple[str, int]:
    """Replace occasional words with `[inaudible]`."""
    tokens = text.split(" ")
    n = 0
    for i, tok in enumerate(tokens):
        if rng.random() < intensity * 0.03 and len(tok) >= 4 and tok.isalpha():
            tokens[i] = "[inaudible]"
            n += 1
    return " ".join(tokens), n


def _apply_speaker_swap(
    lines: list[str], intensity: float, rng: random.Random
) -> tuple[list[str], int]:
    """Swap speaker labels on some lines.

    Only affects lines that look like "Speaker: utterance". Picks a
    random pair of adjacent turns and swaps their labels.
    """
    n = 0
    pattern = re.compile(r"^([A-Za-z][A-Za-z ]{0,20}):\s*(.+)$")
    for i in range(len(lines) - 1):
        if rng.random() >= intensity * 0.08:
            continue
        m1 = pattern.match(lines[i])
        m2 = pattern.match(lines[i + 1])
        if not m1 or not m2 or m1.group(1) == m2.group(1):
            continue
        lines[i] = f"{m2.group(1)}: {m1.group(2)}"
        lines[i + 1] = f"{m1.group(1)}: {m2.group(2)}"
        n += 1
    return lines, n


def _apply_crosstalk(
    lines: list[str], intensity: float, rng: random.Random
) -> tuple[list[str], int]:
    """Merge adjacent turns into a crosstalk line at a low rate."""
    n = 0
    out: list[str] = []
    i = 0
    while i < len(lines):
        if (
            i + 1 < len(lines)
            and rng.random() < intensity * 0.04
            and ":" in lines[i]
            and ":" in lines[i + 1]
        ):
            merged = f"{lines[i]} [crosstalk] {lines[i + 1]}"
            out.append(merged)
            i += 2
            n += 1
        else:
            out.append(lines[i])
            i += 1
    return out, n


def _apply_background(text: str, intensity: float, rng: random.Random) -> tuple[str, int]:
    """Insert background noise markers between sentences."""
    n = 0
    sentences = re.split(r"(?<=[.!?])\s+", text)
    for i in range(len(sentences) - 1):
        if rng.random() < intensity * 0.05:
            sentences[i] = sentences[i] + " [background noise]"
            n += 1
    return " ".join(sentences), n
