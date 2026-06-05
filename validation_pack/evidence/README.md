# Validation Evidence Trail

This directory records reproducible agreement evidence for the validation
corpus. The intended trail is:

```text
case packet -> blinded submission -> Scribeval score -> clinician rating -> agreement statistic
```

The current `synthetic_agreement_v0` files are illustrative bootstrap data. They
exercise the evidence format and calibration workflow, but they are not
independent clinical validation.

For real clinician ratings, keep reviewer provenance outside the scoring
worksheet by using `../reviewer_registry_template.csv`. Reviewer IDs should be
pseudonymous and must not expose names, contact details, provider numbers, or
registration numbers. The stricter import path is:

```bash
python scripts/import_validation_ratings.py \
  --worksheet <filled_worksheet.csv> \
  --judge-scores <scribeval_scores.json> \
  --reviewer-registry <reviewer_registry.csv> \
  --require-qualified-reviewers \
  --output <calibration_pairs.json>
```

## Files

| File | Purpose |
|---|---|
| `evidence_manifest.json` | Versioned metadata and source files |
| `synthetic_reviewer_worksheet_v0.csv` | Filled synthetic reviewer worksheet fixture |
| `synthetic_scribeval_scores_v0.json` | Synthetic Scribeval score export fixture |
| `calibration_pairs_v0.json` | Judge-vs-reviewer score pairs with case/submission references |
| `calibration_report_v0.md` | Rendered interpretation of the calibration pairs |

## Reproduce

```bash
python scripts/import_validation_ratings.py \
  --worksheet validation_pack/evidence/synthetic_reviewer_worksheet_v0.csv \
  --judge-scores validation_pack/evidence/synthetic_scribeval_scores_v0.json \
  --output validation_pack/evidence/calibration_pairs_v0.json
scribeval calibrate validation_pack/evidence/calibration_pairs_v0.json
python scripts/validation_pack_audit.py
```
