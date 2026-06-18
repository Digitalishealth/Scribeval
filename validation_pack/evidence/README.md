# Validation Evidence Trail

This directory records reproducible agreement evidence for the validation
corpus. The intended trail is:

```text
case packet -> blinded submission -> Scribeval score -> clinician rating -> agreement statistic
           -> stratified evidence summary
```

The current `synthetic_agreement_v0` files are illustrative bootstrap data. They
exercise the evidence format and calibration workflow, but they are not
independent clinical validation.

For real clinician ratings, keep reviewer provenance outside the scoring
worksheet by using `../reviewer_registry_template.csv`. Reviewer IDs should be
pseudonymous and must not expose names, contact details, provider numbers, or
registration numbers. First generate reviewer-specific assignment worksheets:

```bash
python scripts/build_reviewer_assignments.py \
  --reviewer-registry <reviewer_registry.csv> \
  --output-dir <reviewer_assignments_dir>
```

After reviewers complete their worksheets, audit the completed review set:

```bash
python scripts/audit_clinician_review_readiness.py \
  --worksheet <filled_worksheet.csv> \
  --reviewer-registry <reviewer_registry.csv> \
  --output-json <readiness_report.json> \
  --output-md <readiness_report.md> \
  --fail-on-not-ready
```

Then use the stricter import path:

```bash
python scripts/export_validation_judge_scores.py \
  --output <scribeval_scores.json> \
  --dimensions omission,hallucination,medicolegal,ahpra,pdqi9,qnote
python scripts/summarize_reviewer_reliability.py \
  --worksheet <filled_worksheet.csv> \
  --reviewer-registry <reviewer_registry.csv> \
  --output-json <reviewer_reliability.json> \
  --output-md <reviewer_reliability.md> \
  --fail-on-not-ready
python scripts/build_consensus_validation_ratings.py \
  --worksheet <filled_worksheet.csv> \
  --reviewer-registry <reviewer_registry.csv> \
  --judge-scores <scribeval_scores.json> \
  --output <consensus_calibration_pairs.json> \
  --output-summary-json <consensus_summary.json> \
  --output-summary-md <consensus_summary.md>
python scripts/build_adjudication_packets.py \
  --consensus-pairs <consensus_calibration_pairs.json> \
  --output-dir <adjudication_packets_dir>
python scripts/import_adjudication_decisions.py \
  --consensus-pairs <consensus_calibration_pairs.json> \
  --adjudication-worksheet <filled_adjudication_worksheet.csv> \
  --reviewer-registry <reviewer_registry.csv> \
  --adjudicator-id <adjudicator_reviewer_id> \
  --require-qualified-adjudicator \
  --output <adjudicated_consensus_calibration_pairs.json> \
  --output-summary-json <adjudicated_consensus_summary.json> \
  --output-summary-md <adjudicated_consensus_summary.md>
python scripts/assess_validation_claim_readiness.py \
  --evidence-manifest <evidence_manifest.json> \
  --output-json <validation_claim_readiness.json> \
  --output-md <validation_claim_readiness.md> \
  --fail-on-not-ready
python scripts/import_validation_ratings.py \
  --worksheet <filled_worksheet.csv> \
  --judge-scores <scribeval_scores.json> \
  --reviewer-registry <reviewer_registry.csv> \
  --require-qualified-reviewers \
  --output <calibration_pairs.json>
python scripts/summarize_validation_evidence.py \
  --output-json <stratified_summary.json> \
  --output-md <stratified_summary.md>
```

For a completed independent clinician run, prefer the bundle builder because it
keeps the readiness report, reviewer reliability report, individual and
consensus calibration pairs, agreement reports, stratified summary, manifest,
claim-readiness assessment, and source hashes together:

```bash
python scripts/build_validation_evidence_bundle.py \
  --run-id <review_run_id> \
  --worksheet <filled_worksheet.csv> \
  --reviewer-registry <reviewer_registry.csv> \
  --judge-scores <scribeval_scores.json> \
  --output-dir validation_pack/evidence_runs
```

Before publishing or committing generated run bundles, audit that they contain
only publishable evidence artifacts and source hashes, not raw clinician CSV
inputs:

```bash
python scripts/audit_validation_evidence_runs.py \
  --evidence-runs validation_pack/evidence_runs
```

Publish a compact index of generated evidence runs so readers can see coverage,
claim-readiness status, and agreement minima across bundles:

```bash
python scripts/index_validation_evidence_runs.py \
  --evidence-runs validation_pack/evidence_runs \
  --output-json validation_pack/evidence_runs/index.json \
  --output-md validation_pack/evidence_runs/index.md
```

## Files

| File | Purpose |
|---|---|
| `evidence_manifest.json` | Versioned metadata and source files |
| `synthetic_reviewer_worksheet_v0.csv` | Filled synthetic reviewer worksheet fixture |
| `synthetic_scribeval_scores_v0.json` | Synthetic Scribeval score export fixture |
| `calibration_pairs_v0.json` | Judge-vs-reviewer score pairs with case/submission references |
| `calibration_report_v0.md` | Rendered interpretation of the calibration pairs |
| `stratified_summary_v0.json` | Agreement coverage by specialty, source, prompt strategy, and failure mode |
| `stratified_summary_v0.md` | Human-readable stratified evidence summary |

## Reproduce

```bash
python scripts/import_validation_ratings.py \
  --worksheet validation_pack/evidence/synthetic_reviewer_worksheet_v0.csv \
  --judge-scores validation_pack/evidence/synthetic_scribeval_scores_v0.json \
  --output validation_pack/evidence/calibration_pairs_v0.json
python scripts/summarize_validation_evidence.py
scribeval calibrate validation_pack/evidence/calibration_pairs_v0.json
python scripts/validation_pack_audit.py
python scripts/audit_validation_evidence_runs.py
```
