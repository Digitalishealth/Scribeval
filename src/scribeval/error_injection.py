"""Programmatic error injection for verifying detection capability.

Takes a clean reference note and introduces known errors from a fixed
taxonomy. This is the feature that lets you make empirical claims like
"we planted 30 errors, Scribeval caught 27". Without this, any claim
about detection capability is unsupported.

Design principles:
- **Deterministic**: same inputs + same seed = same corrupted output.
  No LLM in this path.
- **Taxonomic**: every injection is tagged with an error type from a
  fixed taxonomy so detection rates can be stratified by category.
- **Reversible**: the injection function returns both the corrupted
  text AND a description of what was changed, so the detection check
  can compare claimed findings against the ground truth.
- **Narrow claim**: this does NOT simulate the full space of real
  scribe failures. It simulates a specific, well-defined subset that
  is useful for regression testing and calibration.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from enum import StrEnum


class ErrorType(StrEnum):
    """Taxonomy of programmatically injected errors."""

    MISSING_ALLERGY = "missing_allergy"
    FABRICATED_FINDING = "fabricated_finding"
    WRONG_DRUG = "wrong_drug"
    WRONG_DOSE = "wrong_dose"
    MISSING_RED_FLAG = "missing_red_flag"
    FABRICATED_MEDICATION = "fabricated_medication"
    OMITTED_MANAGEMENT_STEP = "omitted_management_step"
    WRONG_LATERALITY = "wrong_laterality"


@dataclass(frozen=True)
class InjectedError:
    """Description of a single error injected into a note."""

    error_type: ErrorType
    description: str
    expected_severity: str  # "critical", "high", "moderate", "low"
    original_text: str | None = None
    replacement_text: str | None = None


@dataclass(frozen=True)
class CorruptedNote:
    """A note with known errors injected into it."""

    original: str
    corrupted: str
    injected_errors: list[InjectedError]

    def as_ground_truth(self) -> list[dict[str, str]]:
        """Return a serialisable list of what was injected."""
        return [
            {
                "error_type": e.error_type.value,
                "description": e.description,
                "expected_severity": e.expected_severity,
            }
            for e in self.injected_errors
        ]


# --------------------------------------------------------------------------- #
# Injection primitives
# --------------------------------------------------------------------------- #


def _inject_missing_allergy(note: str) -> tuple[str, InjectedError] | None:
    """Remove an allergy mention from the note, if one exists."""
    patterns = [
        r"(?i)\ballergies?\s*:.*?(?=\n\n|\n[A-Z]|$)",
        r"(?i)\ballergic to\b[^.\n]*[.\n]",
        r"(?i)\bpenicillin allerg[yi]\w*[^.\n]*[.\n]",
        r"(?i)\bNKDA\b[^.\n]*[.\n]?",
    ]
    for pattern in patterns:
        m = re.search(pattern, note, flags=re.DOTALL)
        if m:
            corrupted = note[: m.start()] + note[m.end() :]
            return corrupted, InjectedError(
                error_type=ErrorType.MISSING_ALLERGY,
                description=f"Removed allergy mention: {m.group(0).strip()[:80]}",
                expected_severity="critical",
                original_text=m.group(0),
                replacement_text="",
            )
    return None


def _inject_fabricated_finding(note: str) -> tuple[str, InjectedError] | None:
    """Add a fabricated objective finding to the note."""
    insertion = (
        "\nExamination also revealed 2/6 systolic murmur loudest at the apex, "
        "radiating to the axilla, not previously documented."
    )
    marker = re.search(r"(?i)\b(examination|exam|o/e|on examination)\b", note)
    if marker:
        insert_at = note.find("\n", marker.end())
        if insert_at == -1:
            insert_at = marker.end()
        corrupted = note[:insert_at] + insertion + note[insert_at:]
    else:
        corrupted = note + insertion
    return corrupted, InjectedError(
        error_type=ErrorType.FABRICATED_FINDING,
        description="Inserted fabricated cardiac murmur not present in transcript",
        expected_severity="critical",
        replacement_text=insertion.strip(),
    )


def _inject_wrong_drug(note: str) -> tuple[str, InjectedError] | None:
    """Replace a real medication name with a different one."""
    drug_swaps = [
        (r"\bamoxicillin\b", "ciprofloxacin", "amoxicillin"),
        (r"\bparacetamol\b", "ibuprofen", "paracetamol"),
        (r"\bsalbutamol\b", "ipratropium", "salbutamol"),
        (r"\bmetformin\b", "glibenclamide", "metformin"),
        (r"\batorvastatin\b", "simvastatin", "atorvastatin"),
    ]
    for pattern, replacement, original in drug_swaps:
        if re.search(pattern, note, flags=re.IGNORECASE):
            corrupted = re.sub(pattern, replacement, note, count=1, flags=re.IGNORECASE)
            return corrupted, InjectedError(
                error_type=ErrorType.WRONG_DRUG,
                description=(
                    f"Replaced '{original}' with '{replacement}' "
                    "(different drug class/use)"
                ),
                expected_severity="critical",
                original_text=original,
                replacement_text=replacement,
            )
    return None


def _inject_wrong_dose(note: str) -> tuple[str, InjectedError] | None:
    """Multiply a numeric dose by 10 — a classic decimal-point error."""
    m = re.search(r"\b(\d+(?:\.\d+)?)\s*(mg|mcg|g|ml)\b", note, flags=re.IGNORECASE)
    if not m:
        return None
    original_value = float(m.group(1))
    new_value = original_value * 10
    new_value_str = str(int(new_value)) if new_value == int(new_value) else str(new_value)
    corrupted = note[: m.start()] + f"{new_value_str}{m.group(2)}" + note[m.end() :]
    return corrupted, InjectedError(
        error_type=ErrorType.WRONG_DOSE,
        description=(
            f"10x dose error: changed {m.group(1)}{m.group(2)} to "
            f"{new_value_str}{m.group(2)}"
        ),
        expected_severity="critical",
        original_text=m.group(0),
        replacement_text=f"{new_value_str}{m.group(2)}",
    )


def _inject_missing_red_flag(note: str) -> tuple[str, InjectedError] | None:
    """Remove a red-flag negative (e.g., 'no chest pain', 'no haematuria')."""
    patterns = [
        r"(?i)\bno (?:chest pain|haemoptysis|haematuria|weight loss|night sweats|"
        r"fever|rigors|melaena|focal neurological|suicidal ideation)[^.\n]*[.\n]?",
        r"(?i)\bdenies (?:chest pain|haemoptysis|haematuria|weight loss|"
        r"suicidal ideation)[^.\n]*[.\n]?",
    ]
    for pattern in patterns:
        m = re.search(pattern, note)
        if m:
            corrupted = note[: m.start()] + note[m.end() :]
            return corrupted, InjectedError(
                error_type=ErrorType.MISSING_RED_FLAG,
                description=f"Removed red-flag negative: {m.group(0).strip()[:80]}",
                expected_severity="high",
                original_text=m.group(0),
                replacement_text="",
            )
    return None


def _inject_fabricated_medication(note: str) -> tuple[str, InjectedError] | None:
    """Invent a medication and add it to the plan section."""
    insertion = (
        "\nNew prescription: Amoxoflavin 500mg BD for 7 days "
        "(non-existent drug for testing)."
    )
    plan_marker = re.search(r"(?i)\b(plan|management|treatment)\b", note)
    if plan_marker:
        insert_at = note.find("\n", plan_marker.end())
        if insert_at == -1:
            insert_at = plan_marker.end()
        corrupted = note[:insert_at] + insertion + note[insert_at:]
    else:
        corrupted = note + insertion
    return corrupted, InjectedError(
        error_type=ErrorType.FABRICATED_MEDICATION,
        description="Inserted non-existent medication 'Amoxoflavin'",
        expected_severity="critical",
        replacement_text=insertion.strip(),
    )


def _inject_omitted_management(note: str) -> tuple[str, InjectedError] | None:
    """Remove a follow-up / safety-netting sentence."""
    patterns = [
        r"(?i)\b(?:review|follow[- ]?up|return)\s+(?:in|after)[^.\n]*[.\n]",
        r"(?i)\bsafety[- ]?net[^.\n]*[.\n]",
        r"(?i)\bif (?:symptoms? worsen|no improvement|develops?)[^.\n]*[.\n]",
    ]
    for pattern in patterns:
        m = re.search(pattern, note)
        if m:
            corrupted = note[: m.start()] + note[m.end() :]
            return corrupted, InjectedError(
                error_type=ErrorType.OMITTED_MANAGEMENT_STEP,
                description=f"Removed follow-up/safety-net: {m.group(0).strip()[:80]}",
                expected_severity="high",
                original_text=m.group(0),
                replacement_text="",
            )
    return None


def _inject_wrong_laterality(note: str) -> tuple[str, InjectedError] | None:
    """Swap left/right in an anatomical reference."""
    if re.search(r"\bleft\b", note, flags=re.IGNORECASE):
        corrupted = re.sub(r"\bleft\b", "right", note, count=1, flags=re.IGNORECASE)
        return corrupted, InjectedError(
            error_type=ErrorType.WRONG_LATERALITY,
            description="Swapped 'left' -> 'right' in anatomical reference",
            expected_severity="high",
            original_text="left",
            replacement_text="right",
        )
    if re.search(r"\bright\b", note, flags=re.IGNORECASE):
        corrupted = re.sub(r"\bright\b", "left", note, count=1, flags=re.IGNORECASE)
        return corrupted, InjectedError(
            error_type=ErrorType.WRONG_LATERALITY,
            description="Swapped 'right' -> 'left' in anatomical reference",
            expected_severity="high",
            original_text="right",
            replacement_text="left",
        )
    return None


INJECTORS = {
    ErrorType.MISSING_ALLERGY: _inject_missing_allergy,
    ErrorType.FABRICATED_FINDING: _inject_fabricated_finding,
    ErrorType.WRONG_DRUG: _inject_wrong_drug,
    ErrorType.WRONG_DOSE: _inject_wrong_dose,
    ErrorType.MISSING_RED_FLAG: _inject_missing_red_flag,
    ErrorType.FABRICATED_MEDICATION: _inject_fabricated_medication,
    ErrorType.OMITTED_MANAGEMENT_STEP: _inject_omitted_management,
    ErrorType.WRONG_LATERALITY: _inject_wrong_laterality,
}


def inject_errors(
    note: str,
    error_types: list[ErrorType] | None = None,
    seed: int | None = None,
) -> CorruptedNote:
    """Inject every error in `error_types` into the note, in a random order.

    Errors that cannot be injected (e.g., wrong_dose when the note has no
    doses) are silently skipped. The returned CorruptedNote only lists
    errors that were actually applied.
    """
    requested = list(error_types) if error_types else list(INJECTORS.keys())
    rng = random.Random(seed)
    rng.shuffle(requested)

    current = note
    applied: list[InjectedError] = []
    for err_type in requested:
        result = INJECTORS[err_type](current)
        if result is None:
            continue
        current, injected = result
        applied.append(injected)

    return CorruptedNote(
        original=note,
        corrupted=current,
        injected_errors=applied,
    )


# --------------------------------------------------------------------------- #
# Detection scoring
# --------------------------------------------------------------------------- #


@dataclass
class DetectionResult:
    """How well a single evaluation report detected the injected errors."""

    total_injected: int
    detected_count: int
    per_type_detection: dict[str, bool]
    undetected: list[InjectedError]
    false_positive_count: int

    @property
    def recall(self) -> float:
        """Fraction of injected errors that were detected."""
        if self.total_injected == 0:
            return 1.0
        return self.detected_count / self.total_injected


def score_detection(
    injected: list[InjectedError],
    findings: list[dict],
) -> DetectionResult:
    """Compare a list of injected errors against findings from an evaluation.

    A finding is considered to have detected an injected error when its
    description mentions the error type keywords or the replacement text.
    This is a deliberately lenient match — the goal is to measure whether
    the evaluator flagged SOMETHING about each injected error, not whether
    it classified it perfectly.
    """
    per_type: dict[str, bool] = {}
    undetected: list[InjectedError] = []
    detected_finding_indexes: set[int] = set()

    for err in injected:
        matched = False
        for idx, finding in enumerate(findings):
            description = (finding.get("description") or "").lower()
            note_excerpt = (finding.get("note_excerpt") or "").lower()
            hay = f"{description} {note_excerpt}"
            if _finding_matches_error(err, hay):
                matched = True
                detected_finding_indexes.add(idx)
                break
        per_type[err.error_type.value] = matched
        if not matched:
            undetected.append(err)

    detected_count = sum(1 for v in per_type.values() if v)
    false_positives = len(findings) - len(detected_finding_indexes)
    return DetectionResult(
        total_injected=len(injected),
        detected_count=detected_count,
        per_type_detection=per_type,
        undetected=undetected,
        false_positive_count=max(0, false_positives),
    )


def _finding_matches_error(err: InjectedError, hay: str) -> bool:
    """Lenient keyword match: does a finding's text refer to this error?"""
    hay = hay.lower()
    type_keywords = {
        ErrorType.MISSING_ALLERGY: ["allergy", "allergies", "allergic", "nkda"],
        ErrorType.FABRICATED_FINDING: [
            "murmur", "fabricat", "invent", "not in transcript", "not mention",
            "without basis", "no evidence",
        ],
        ErrorType.WRONG_DRUG: ["wrong drug", "different drug", "incorrect medication"],
        ErrorType.WRONG_DOSE: ["dose", "dosage", "strength", "10x", "tenfold"],
        ErrorType.MISSING_RED_FLAG: [
            "red flag", "red-flag", "not documented", "omission", "missing negative"
        ],
        ErrorType.FABRICATED_MEDICATION: [
            "fabricat", "not a real", "non-existent", "invent", "amoxoflavin"
        ],
        ErrorType.OMITTED_MANAGEMENT_STEP: [
            "follow-up", "followup", "safety net", "review", "missing plan"
        ],
        ErrorType.WRONG_LATERALITY: ["laterality", "left", "right", "side"],
    }
    for kw in type_keywords.get(err.error_type, []):
        if kw in hay:
            return True
    if err.replacement_text and err.replacement_text.strip().lower() in hay:
        return True
    return bool(
        err.original_text and err.original_text.strip().lower() in hay
    )
