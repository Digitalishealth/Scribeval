"""Inter-rater agreement statistics for calibrating the judge against humans.

This module provides the statistical primitives needed to run a
calibration study: Cohen's weighted kappa for categorical severity
ratings and intraclass correlation (ICC(2,1) / absolute agreement) for
continuous dimension scores.

No external stats dependency. These implementations are written to be
auditable in a handful of lines of Python — the intent is that a
reviewer can verify the formulas against any textbook without trusting
a package. For production biostatistics use an established package.

Scope:
- Cohen's weighted kappa with linear or quadratic weights
- ICC(2,1) for absolute agreement between two raters
- Simple per-dimension agreement report

Not in scope:
- Multi-rater Fleiss' kappa (only 2 raters here)
- Bootstrap confidence intervals (simple SE from variance components)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

SEVERITY_ORDER: list[str] = ["none", "low", "moderate", "high", "critical"]


class WeightScheme(StrEnum):
    LINEAR = "linear"
    QUADRATIC = "quadratic"


# --------------------------------------------------------------------------- #
# Cohen's weighted kappa
# --------------------------------------------------------------------------- #


def weighted_kappa(
    rater_a: list[str],
    rater_b: list[str],
    categories: list[str] = SEVERITY_ORDER,
    weights: WeightScheme = WeightScheme.LINEAR,
) -> float:
    """Cohen's weighted kappa between two raters on ordered categorical data.

    Inputs are lists of equal length containing category labels (e.g.,
    ["none", "moderate", "critical", ...]). Unknown labels raise a
    ValueError — silent mismatches would corrupt the agreement statistic.
    """
    if len(rater_a) != len(rater_b):
        raise ValueError("Rater lists must be the same length")
    if not rater_a:
        raise ValueError("Cannot compute kappa on an empty rating set")
    n_cat = len(categories)
    index = {c: i for i, c in enumerate(categories)}
    for r in rater_a + rater_b:
        if r not in index:
            raise ValueError(f"Unknown category '{r}'. Expected one of {categories}")

    # Confusion matrix
    observed = [[0] * n_cat for _ in range(n_cat)]
    for a, b in zip(rater_a, rater_b, strict=True):
        observed[index[a]][index[b]] += 1

    n = len(rater_a)
    row_marginals = [sum(row) for row in observed]
    col_marginals = [sum(observed[i][j] for i in range(n_cat)) for j in range(n_cat)]

    # Weight matrix
    max_dist = n_cat - 1
    w_matrix = [[0.0] * n_cat for _ in range(n_cat)]
    for i in range(n_cat):
        for j in range(n_cat):
            dist = abs(i - j)
            if weights == WeightScheme.LINEAR:
                w_matrix[i][j] = 1.0 - dist / max_dist if max_dist > 0 else 0.0
            else:
                w_matrix[i][j] = 1.0 - (dist / max_dist) ** 2 if max_dist > 0 else 0.0

    observed_agreement = sum(
        w_matrix[i][j] * observed[i][j] for i in range(n_cat) for j in range(n_cat)
    ) / n
    expected_agreement = sum(
        w_matrix[i][j] * (row_marginals[i] * col_marginals[j]) / (n * n)
        for i in range(n_cat)
        for j in range(n_cat)
    )

    if abs(1 - expected_agreement) < 1e-12:
        return 1.0 if observed_agreement >= 1.0 - 1e-12 else 0.0
    return (observed_agreement - expected_agreement) / (1 - expected_agreement)


# --------------------------------------------------------------------------- #
# Intraclass correlation ICC(2,1)
# --------------------------------------------------------------------------- #


def icc_2_1(
    rater_a: list[float], rater_b: list[float]
) -> float:
    """ICC(2,1) absolute agreement between two raters on continuous scores.

    Two-way random effects model, single rater, absolute agreement.
    Formula: (MSR - MSE) / (MSR + (k-1)*MSE + k*(MSC - MSE)/n)

    Where k=2 raters, n=subjects, MSR=between-subject MS, MSE=residual MS,
    MSC=between-rater MS. See Shrout & Fleiss (1979).
    """
    if len(rater_a) != len(rater_b):
        raise ValueError("Rater lists must be the same length")
    n = len(rater_a)
    if n < 2:
        raise ValueError("ICC requires at least 2 subjects")
    k = 2

    subject_means = [(a + b) / 2 for a, b in zip(rater_a, rater_b, strict=True)]
    rater_means = [sum(rater_a) / n, sum(rater_b) / n]
    grand_mean = sum(rater_means) / 2

    ss_between_subjects = k * sum((s - grand_mean) ** 2 for s in subject_means)
    ms_r = ss_between_subjects / (n - 1)

    ss_between_raters = n * sum((rm - grand_mean) ** 2 for rm in rater_means)
    ms_c = ss_between_raters / (k - 1)

    ss_total = sum((a - grand_mean) ** 2 for a in rater_a) + sum(
        (b - grand_mean) ** 2 for b in rater_b
    )
    ss_error = ss_total - ss_between_subjects - ss_between_raters
    df_error = (n - 1) * (k - 1)
    ms_e = ss_error / df_error if df_error > 0 else 0.0

    denominator = ms_r + (k - 1) * ms_e + k * (ms_c - ms_e) / n
    if abs(denominator) < 1e-12:
        return 0.0
    return (ms_r - ms_e) / denominator


# --------------------------------------------------------------------------- #
# Top-level agreement report
# --------------------------------------------------------------------------- #


@dataclass
class DimensionAgreement:
    """Per-dimension agreement between two raters."""

    dimension: str
    n_pairs: int
    kappa: float
    icc: float
    mean_abs_difference: float
    judge_mean: float
    human_mean: float

    def interpret_kappa(self) -> str:
        """Landis & Koch (1977) interpretation of kappa values."""
        k = self.kappa
        if k < 0:
            return "poor"
        if k < 0.20:
            return "slight"
        if k < 0.40:
            return "fair"
        if k < 0.60:
            return "moderate"
        if k < 0.80:
            return "substantial"
        return "almost perfect"


@dataclass
class RatingPair:
    """One subject's score pair for agreement calculation."""

    dimension: str
    judge_score: float
    human_score: float
    judge_severity: str
    human_severity: str


def compute_agreement(pairs: list[RatingPair]) -> list[DimensionAgreement]:
    """Compute per-dimension agreement across a set of rating pairs."""
    by_dim: dict[str, list[RatingPair]] = {}
    for p in pairs:
        by_dim.setdefault(p.dimension, []).append(p)

    out: list[DimensionAgreement] = []
    for dim, ps in sorted(by_dim.items()):
        judge = [p.judge_score for p in ps]
        human = [p.human_score for p in ps]
        judge_sev = [p.judge_severity for p in ps]
        human_sev = [p.human_severity for p in ps]
        try:
            kappa = weighted_kappa(judge_sev, human_sev)
        except ValueError:
            kappa = float("nan")
        try:
            icc = icc_2_1(judge, human)
        except ValueError:
            icc = float("nan")
        out.append(
            DimensionAgreement(
                dimension=dim,
                n_pairs=len(ps),
                kappa=round(kappa, 4) if not math.isnan(kappa) else 0.0,
                icc=round(icc, 4) if not math.isnan(icc) else 0.0,
                mean_abs_difference=round(
                    sum(abs(a - b) for a, b in zip(judge, human, strict=True))
                    / len(ps),
                    4,
                ),
                judge_mean=round(sum(judge) / len(judge), 4),
                human_mean=round(sum(human) / len(human), 4),
            )
        )
    return out
