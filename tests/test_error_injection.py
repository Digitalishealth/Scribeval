"""Tests for deterministic error injection and detection scoring."""

from __future__ import annotations

from scribeval.error_injection import (
    ErrorType,
    InjectedError,
    inject_errors,
    score_detection,
)

SAMPLE_NOTE = """Consultation Note

Allergies: Penicillin — causes rash.
Medications: amoxicillin 500mg TDS, paracetamol 500mg PRN.

History:
Patient presents with cough. Denies chest pain. No haemoptysis.

Examination:
Left tympanic membrane red and dull.
Temperature 37.5, heart rate 80.

Plan:
1. Amoxicillin 500mg TDS for 7 days.
2. Review in 1 week if no improvement.
"""


def test_inject_errors_is_deterministic() -> None:
    a = inject_errors(SAMPLE_NOTE, seed=42)
    b = inject_errors(SAMPLE_NOTE, seed=42)
    assert a.corrupted == b.corrupted
    assert [e.error_type for e in a.injected_errors] == [
        e.error_type for e in b.injected_errors
    ]


def test_inject_errors_changes_note() -> None:
    result = inject_errors(SAMPLE_NOTE, seed=1)
    assert result.corrupted != SAMPLE_NOTE
    assert len(result.injected_errors) >= 1


def test_inject_errors_skips_inapplicable() -> None:
    # Note with no doses — wrong_dose injector should silently skip.
    note = "Patient has a cough. No medications."
    result = inject_errors(note, error_types=[ErrorType.WRONG_DOSE], seed=0)
    assert result.corrupted == note
    assert result.injected_errors == []


def test_inject_missing_allergy_removes_allergy_line() -> None:
    result = inject_errors(
        SAMPLE_NOTE, error_types=[ErrorType.MISSING_ALLERGY], seed=0
    )
    assert len(result.injected_errors) == 1
    assert "penicillin" not in result.corrupted.lower()


def test_inject_wrong_drug_replaces_med() -> None:
    result = inject_errors(
        SAMPLE_NOTE, error_types=[ErrorType.WRONG_DRUG], seed=0
    )
    assert len(result.injected_errors) == 1
    # At least one expected drug swap must have been applied
    assert (
        "ciprofloxacin" in result.corrupted.lower()
        or "ibuprofen" in result.corrupted.lower()
    )


def test_inject_wrong_dose_multiplies_by_10() -> None:
    note = "Amoxicillin 500mg TDS"
    result = inject_errors(
        note, error_types=[ErrorType.WRONG_DOSE], seed=0
    )
    assert len(result.injected_errors) == 1
    assert "5000mg" in result.corrupted


def test_score_detection_recall_all_detected() -> None:
    errors = [
        InjectedError(
            error_type=ErrorType.MISSING_ALLERGY,
            description="Removed allergy",
            expected_severity="critical",
        ),
        InjectedError(
            error_type=ErrorType.WRONG_DOSE,
            description="10x dose error",
            expected_severity="critical",
        ),
    ]
    findings = [
        {"description": "Allergy status not documented", "note_excerpt": ""},
        {"description": "Unusual dose strength noted", "note_excerpt": ""},
    ]
    result = score_detection(errors, findings)
    assert result.recall == 1.0
    assert result.detected_count == 2


def test_score_detection_recall_zero_detected() -> None:
    errors = [
        InjectedError(
            error_type=ErrorType.MISSING_ALLERGY,
            description="Removed allergy",
            expected_severity="critical",
        ),
    ]
    findings = [
        {"description": "Note is brief", "note_excerpt": ""},
    ]
    result = score_detection(errors, findings)
    assert result.recall == 0.0
    assert result.undetected == errors
