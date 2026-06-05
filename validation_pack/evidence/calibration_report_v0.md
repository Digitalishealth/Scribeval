# Synthetic Agreement Evidence v0

This report is generated from `calibration_pairs_v0.json`.

It is a reproducibility fixture and evidence-trail example only. The reviewer
ratings are synthetic and must be replaced with independent clinician ratings
before making clinical validation claims.

Command:

```bash
scribeval calibrate validation_pack/evidence/calibration_pairs_v0.json
```

## Agreement Summary

| Dimension | N | Weighted kappa | Kappa interpretation | ICC(2,1) | Mean absolute difference |
|---|---:|---:|---|---:|---:|
| ahpra | 13 | 1.000 | almost perfect | 0.938 | 0.032 |
| hallucination | 13 | 1.000 | almost perfect | 0.984 | 0.031 |
| medication_terminology | 9 | 1.000 | almost perfect | 0.982 | 0.030 |
| medicolegal | 25 | 0.961 | almost perfect | 0.965 | 0.036 |
| omission | 26 | 0.870 | almost perfect | 0.985 | 0.033 |
| pdqi9 | 11 | 1.000 | almost perfect | 0.160 | 0.030 |
| qnote | 21 | 1.000 | almost perfect | 0.909 | 0.028 |

## Interpretation

The synthetic pairs show how the evidence trail is intended to work across
case packets, blinded submissions, dimensions, and reviewer ratings.

The PDQI-9 row intentionally demonstrates a real interpretation issue: a small
mean absolute difference can coexist with a low ICC when the synthetic examples
have a narrow score range. Real validation reports should review both agreement
statistics and the underlying score distribution before drawing conclusions.

## Coverage

- 20 synthetic case packets
- 100 blinded submissions
- Nurse + CDSS and model-candidate note sources
- Standard, structured SOAP, safety-first, CDSS-informed, and checklist prompt
  strategies
- Omission, hallucination, medication terminology, medicolegal, AHPRA, PDQI-9,
  and QNOTE dimensions
