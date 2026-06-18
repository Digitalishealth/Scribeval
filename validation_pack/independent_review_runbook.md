# Independent Clinician Review Runbook

This runbook defines the coordinator workflow for converting the public
Scribeval validation corpus into an independent clinician evidence run.

Benchmark unit: `whole transcript -> final note quality score`

## Claim Boundary

This runbook supports reproducible evidence collection only. It is not
validation evidence until a completed independent clinician evidence bundle
passes validation-claim readiness.

## Private Input Policy

Keep private collection material out of the public repository. The following
paths are ignored by Git and are intended for coordinator-only work:

- `validation_pack/reviewer_assignments/`
- `validation_pack/private_review_inputs/`
- `validation_pack/private_review_runs/`

Never commit named reviewer records, reviewer contact details, registration
numbers, signed consent forms, source registration verification documents, raw
filled reviewer worksheets, reviewer-specific assignment worksheets, payment
records, or raw adjudication worksheets.

Publish only aggregate readiness reports, aggregate reliability reports,
adjudicated consensus calibration pairs, adjudication burden summaries,
validation claim readiness reports, evidence manifests with source hashes, and
evidence-run indexes.

## Stages

| Stage | Exit Evidence |
|---|---|
| prepare public materials | `validation_pack_audit.py` passes and the collection plan has no underpowered stratum values |
| onboard reviewers | reviewer intake, attestation, and training are complete, with private eligibility records retained outside the public repository |
| generate private assignments | `assignment_manifest.json` records two qualified reviewers per case-submission in an ignored private path |
| collect blinded ratings | all assigned worksheets are returned with overall and required dimension ratings complete |
| export judge scores | Scribeval score JSON covers every required case-submission and contains no raw transcript or note text |
| check review readiness | clinician review readiness audit passes and review-run status has no readiness issue counts |
| estimate reviewer reliability | reviewer reliability report meets prespecified thresholds or documents failed thresholds |
| build consensus and adjudicate | all adjudication-required rows are resolved with qualified pseudonymous adjudicator provenance |
| build public evidence bundle | evidence bundle contains source hashes and excludes raw reviewer CSV inputs |
| publish evidence index | evidence run audit passes and index exposes claim readiness plus failed readiness checks |
| assess goal status | validation goal status is claim-ready only when an independent clinician evidence run passes readiness |

## Command Sequence

```bash
python scripts/build_reviewer_packets.py
python scripts/plan_validation_collection.py \
  --output-json validation_pack/collection_plan.json \
  --output-md validation_pack/collection_plan.md \
  --fail-on-underpowered
python scripts/validation_pack_audit.py

python scripts/build_reviewer_assignments.py \
  --reviewer-registry validation_pack/private_review_inputs/reviewer_registry.csv \
  --output-dir validation_pack/reviewer_assignments

python scripts/export_validation_judge_scores.py \
  --output validation_pack/private_review_runs/scribeval_scores.json \
  --dimensions omission,hallucination,medicolegal,ahpra,pdqi9,qnote

python scripts/audit_clinician_review_readiness.py \
  --worksheet validation_pack/private_review_inputs/filled_worksheet.csv \
  --reviewer-registry validation_pack/private_review_inputs/reviewer_registry.csv \
  --output-json validation_pack/private_review_runs/readiness_report.json \
  --output-md validation_pack/private_review_runs/readiness_report.md \
  --fail-on-not-ready

python scripts/summarize_validation_review_run.py \
  --reviewer-registry validation_pack/private_review_inputs/reviewer_registry.csv \
  --assignments-dir validation_pack/reviewer_assignments \
  --worksheet validation_pack/private_review_inputs/filled_worksheet.csv \
  --judge-scores validation_pack/private_review_runs/scribeval_scores.json \
  --output-json validation_pack/private_review_runs/review_run_status.json \
  --output-md validation_pack/private_review_runs/review_run_status.md \
  --fail-on-not-ready

python scripts/summarize_reviewer_reliability.py \
  --worksheet validation_pack/private_review_inputs/filled_worksheet.csv \
  --reviewer-registry validation_pack/private_review_inputs/reviewer_registry.csv \
  --output-json validation_pack/private_review_runs/reviewer_reliability.json \
  --output-md validation_pack/private_review_runs/reviewer_reliability.md \
  --fail-on-not-ready

python scripts/build_consensus_validation_ratings.py \
  --worksheet validation_pack/private_review_inputs/filled_worksheet.csv \
  --reviewer-registry validation_pack/private_review_inputs/reviewer_registry.csv \
  --judge-scores validation_pack/private_review_runs/scribeval_scores.json \
  --output validation_pack/private_review_runs/consensus_calibration_pairs.json \
  --output-summary-json validation_pack/private_review_runs/consensus_summary.json \
  --output-summary-md validation_pack/private_review_runs/consensus_summary.md

python scripts/build_adjudication_packets.py \
  --consensus-pairs validation_pack/private_review_runs/consensus_calibration_pairs.json \
  --output-dir validation_pack/private_review_runs/adjudication_packets

python scripts/import_adjudication_decisions.py \
  --consensus-pairs validation_pack/private_review_runs/consensus_calibration_pairs.json \
  --adjudication-worksheet validation_pack/private_review_inputs/filled_adjudication_worksheet.csv \
  --reviewer-registry validation_pack/private_review_inputs/reviewer_registry.csv \
  --adjudicator-id <adjudicator_reviewer_id> \
  --require-qualified-adjudicator \
  --output validation_pack/private_review_runs/adjudicated_consensus_calibration_pairs.json \
  --output-summary-json validation_pack/private_review_runs/adjudicated_consensus_summary.json \
  --output-summary-md validation_pack/private_review_runs/adjudicated_consensus_summary.md

python scripts/build_validation_evidence_bundle.py \
  --run-id <review_run_id> \
  --worksheet validation_pack/private_review_inputs/filled_worksheet.csv \
  --reviewer-registry validation_pack/private_review_inputs/reviewer_registry.csv \
  --judge-scores validation_pack/private_review_runs/scribeval_scores.json \
  --reviewer-assignments-dir validation_pack/reviewer_assignments \
  --adjudicated-consensus-pairs validation_pack/private_review_runs/adjudicated_consensus_calibration_pairs.json \
  --output-dir validation_pack/evidence_runs

python scripts/audit_validation_evidence_runs.py \
  --evidence-runs validation_pack/evidence_runs
python scripts/index_validation_evidence_runs.py \
  --evidence-runs validation_pack/evidence_runs \
  --output-json validation_pack/evidence_runs/index.json \
  --output-md validation_pack/evidence_runs/index.md
python scripts/summarize_validation_goal_status.py \
  --output-json validation_pack/validation_goal_status.json \
  --output-md validation_pack/validation_goal_status.md
```
