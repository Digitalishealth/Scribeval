# Example Calibration Report

This report is generated from `example_calibration_pairs.json` and demonstrates
the shape of a clinician validation output. The pairs are synthetic and should
not be interpreted as evidence that Scribeval is clinically validated.

Command:

```bash
scribeval calibrate validation_pack/results/example_calibration_pairs.json
```

## Agreement Summary

| Dimension | N | Weighted kappa | Kappa interpretation | ICC(2,1) | Mean absolute difference |
|---|---:|---:|---|---:|---:|
| ahpra | 8 | 0.886 | almost perfect | 0.956 | 0.031 |
| hallucination | 8 | 0.915 | almost perfect | 0.971 | 0.033 |
| medicolegal | 8 | 0.795 | substantial | 0.953 | 0.041 |
| omission | 8 | 0.714 | substantial | 0.956 | 0.036 |
| pdqi9 | 8 | 0.750 | substantial | 0.942 | 0.036 |
| qnote | 8 | 0.902 | almost perfect | 0.953 | 0.040 |

## How to Read This

- Weighted kappa compares Scribeval and clinician severity ratings.
- ICC(2,1) compares absolute agreement on continuous 0-1 scores.
- Mean absolute difference is the average score gap between Scribeval and the
  clinician reviewer.

For a real validation pilot, run the same report on independent clinician
ratings, review low-agreement dimensions, and keep the blinded case packets and
adjudication notes with the governance record.

