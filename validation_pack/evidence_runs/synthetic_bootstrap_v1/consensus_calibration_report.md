# Clinician Consensus Validation Ratings: synthetic_bootstrap_v1

Consensus ratings average qualified clinician scores for each blinded case-submission-dimension and use consensus severity as the clinical comparator. Rows flagged for adjudication should be reviewed before strong validation claims are made.

## Coverage

- Cases: 20
- Submissions: 100
- Consensus pairs: 700
- Adjudication required: 47
- Dimensions: ahpra, hallucination, medicolegal, omission, overall, pdqi9, qnote

## Judge vs Consensus Agreement

| Dimension | N | Weighted kappa | Kappa interpretation | ICC(2,1) | Mean abs diff |
|---|---:|---:|---|---:|---:|
| ahpra | 100 | 1.000 | almost perfect | 1.000 | 0.000 |
| hallucination | 100 | 1.000 | almost perfect | 1.000 | 0.000 |
| medicolegal | 100 | 0.911 | almost perfect | 0.995 | 0.020 |
| omission | 100 | 0.979 | almost perfect | 0.992 | 0.020 |
| overall | 100 | 0.827 | almost perfect | 0.998 | 0.010 |
| pdqi9 | 100 | 1.000 | almost perfect | 1.000 | 0.000 |
| qnote | 100 | 0.989 | almost perfect | 0.992 | 0.020 |
