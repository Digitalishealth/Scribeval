# Validation Evidence Trail

This directory records reproducible agreement evidence for the validation
corpus. The intended trail is:

```text
case packet -> blinded submission -> Scribeval score -> clinician rating -> agreement statistic
```

The current `synthetic_agreement_v0` files are illustrative bootstrap data. They
exercise the evidence format and calibration workflow, but they are not
independent clinical validation.

## Files

| File | Purpose |
|---|---|
| `evidence_manifest.json` | Versioned metadata and source files |
| `calibration_pairs_v0.json` | Judge-vs-reviewer score pairs with case/submission references |
| `calibration_report_v0.md` | Rendered interpretation of the calibration pairs |

## Reproduce

```bash
scribeval calibrate validation_pack/evidence/calibration_pairs_v0.json
python scripts/validation_pack_audit.py
```

