"""Tests for the ASR noise simulator."""

from __future__ import annotations

from scribeval.asr_noise import NoiseType, apply_asr_noise

SAMPLE = """Doctor: Patient has dysuria and hypertension.
Patient: I've been coughing too.
Doctor: Any chest pain?
Patient: No chest pain.
"""


def test_zero_intensity_is_noop() -> None:
    out, report = apply_asr_noise(SAMPLE, intensity=0.0, seed=1)
    assert out == SAMPLE
    assert report.total_edits == 0


def test_noise_is_deterministic_with_seed() -> None:
    a, _ = apply_asr_noise(SAMPLE, intensity=0.5, seed=42)
    b, _ = apply_asr_noise(SAMPLE, intensity=0.5, seed=42)
    assert a == b


def test_noise_actually_modifies_with_high_intensity() -> None:
    out, report = apply_asr_noise(SAMPLE * 5, intensity=0.9, seed=7)
    # With 5x the input and intensity 0.9 some edit is effectively certain.
    assert out != SAMPLE * 5
    assert report.total_edits > 0


def test_type_filter_restricts_noise() -> None:
    out, report = apply_asr_noise(
        SAMPLE * 4, intensity=0.9, seed=7, types=[NoiseType.FILLER]
    )
    assert set(report.edits_by_type.keys()) <= {NoiseType.FILLER.value}


def test_intensity_clamped_to_one() -> None:
    out, report = apply_asr_noise(SAMPLE, intensity=10.0, seed=1)
    assert report.intensity == 1.0
