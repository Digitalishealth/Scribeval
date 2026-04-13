"""Tests for inter-rater agreement statistics."""

from __future__ import annotations

import math

import pytest

from scribeval.calibration import (
    RatingPair,
    WeightScheme,
    compute_agreement,
    icc_2_1,
    weighted_kappa,
)


def test_weighted_kappa_perfect_agreement() -> None:
    a = ["none", "low", "moderate", "high", "critical"]
    b = ["none", "low", "moderate", "high", "critical"]
    k = weighted_kappa(a, b)
    assert k == pytest.approx(1.0, abs=1e-9)


def test_weighted_kappa_complete_disagreement() -> None:
    a = ["none"] * 5
    b = ["critical"] * 5
    k = weighted_kappa(a, b)
    # Expected agreement equals observed when marginals are single-category,
    # so kappa is defined to be 0 here.
    assert k <= 0.0


def test_weighted_kappa_linear_vs_quadratic_differ() -> None:
    a = ["none", "low", "moderate", "high", "critical"]
    b = ["low", "none", "high", "moderate", "critical"]
    k_lin = weighted_kappa(a, b, weights=WeightScheme.LINEAR)
    k_quad = weighted_kappa(a, b, weights=WeightScheme.QUADRATIC)
    # Different weightings should not produce identical coefficients in
    # the general case.
    assert k_lin != k_quad


def test_weighted_kappa_rejects_mismatched_lengths() -> None:
    with pytest.raises(ValueError):
        weighted_kappa(["none"], ["none", "none"])


def test_weighted_kappa_rejects_unknown_category() -> None:
    with pytest.raises(ValueError):
        weighted_kappa(["whatever"], ["none"])


def test_icc_perfect_agreement() -> None:
    a = [0.1, 0.3, 0.5, 0.7, 0.9]
    b = [0.1, 0.3, 0.5, 0.7, 0.9]
    icc = icc_2_1(a, b)
    assert icc == pytest.approx(1.0, abs=1e-9)


def test_icc_rejects_too_few_subjects() -> None:
    with pytest.raises(ValueError):
        icc_2_1([0.5], [0.5])


def test_icc_partial_agreement_positive() -> None:
    a = [0.2, 0.4, 0.6, 0.8]
    b = [0.25, 0.45, 0.55, 0.75]
    icc = icc_2_1(a, b)
    assert 0.0 < icc <= 1.0


def test_compute_agreement_per_dimension() -> None:
    pairs = [
        RatingPair("omission", 0.9, 0.85, "low", "low"),
        RatingPair("omission", 0.7, 0.75, "moderate", "moderate"),
        RatingPair("omission", 0.5, 0.55, "high", "moderate"),
        RatingPair("hallucination", 0.95, 1.0, "none", "none"),
        RatingPair("hallucination", 0.8, 0.85, "low", "low"),
        RatingPair("hallucination", 0.6, 0.65, "moderate", "moderate"),
    ]
    agreements = compute_agreement(pairs)
    dims = {a.dimension for a in agreements}
    assert dims == {"omission", "hallucination"}
    for a in agreements:
        assert a.n_pairs == 3
        assert not math.isnan(a.kappa)
        assert -1.0 <= a.kappa <= 1.0
