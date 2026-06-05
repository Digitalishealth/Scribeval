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
| ahpra | 3 | 1.000 | almost perfect | 0.937 | 0.033 |
| hallucination | 4 | 1.000 | almost perfect | 0.993 | 0.025 |
| medicolegal | 4 | 1.000 | almost perfect | 0.970 | 0.033 |
| omission | 5 | 0.783 | substantial | 0.992 | 0.028 |
| pdqi9 | 3 | 1.000 | almost perfect | 0.342 | 0.030 |
| qnote | 4 | 1.000 | almost perfect | 0.969 | 0.022 |

## Interpretation

The synthetic pairs show how the evidence trail is intended to work across
case packets, blinded submissions, dimensions, and reviewer ratings.

The PDQI-9 row intentionally demonstrates a real interpretation issue: a small
mean absolute difference can coexist with a low ICC when the synthetic examples
have a narrow score range. Real validation reports should review both agreement
statistics and the underlying score distribution before drawing conclusions.

## Coverage

- 4 synthetic case packets
- 20 blinded submissions
- Nurse + CDSS and model-candidate note sources
- Standard, structured SOAP, safety-first, CDSS-informed, and checklist prompt
  strategies
- Omission, hallucination, medicolegal, AHPRA, PDQI-9, and QNOTE dimensions

