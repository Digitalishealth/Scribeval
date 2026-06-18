# Scribeval Clinician Validation Pack

This pack is for running a blinded clinician calibration pilot against
Scribeval. It is designed to answer the clinical critique: do Scribeval's
scores and severity ratings agree with qualified human reviewers?

The pack is synthetic and protocol-oriented. It does not contain real patient
data and is not itself evidence of clinical validation.

## Validation Question

For each case, reviewers score final notes against the whole consultation
transcript. The unit of review is:

```text
whole transcript -> final note quality score
```

Each candidate note is scored on the same dimensions used by Scribeval:

- overall note quality
- omission
- hallucination
- medicolegal adequacy
- AHPRA compliance
- PDQI-9
- QNOTE
- optional AMT medication terminology

## Pilot Design

The pilot manifest in `case_manifest.json` defines 20 synthetic review cases
across GP, urgent care, paediatrics, chronic disease, mental health,
palliative care, telehealth, and medication-safety scenarios.

Each case supports up to 5 blinded submissions:

- one Nurse + CDSS baseline submission
- four product-agnostic model or scribe submissions

The submission identities are held back from reviewers. A coordinator can map
`Submission A` to `Submission E` to any scribe, model, prompt strategy, or
clinician workflow being studied. This keeps the pack compatible with
Scribeval's 2-to-5 comparison limit and avoids implying a fixed vendor set.

## Reviewer Workflow

1. De-identify all source material before review.
2. Generate blinded reviewer packets:

```bash
python scripts/build_reviewer_packets.py
```

3. Give reviewers `reviewer_packets/`, `reviewer_scoring_guide.md`, plus
   `reviewer_worksheet.csv` or an imported spreadsheet copy.
4. Ask reviewers to score each blinded submission against the transcript, not
   against another note.
5. Assign each reviewer a pseudonymous `reviewer_id` and record eligibility in
   `reviewer_registry_template.csv`. Do not store names, contact details,
   provider numbers, or registration numbers in this public evidence trail.
6. Complete the coordinator-side intake controls in
   `reviewer_intake_checklist.json` before distributing assignments. Keep
   signed consent, source registration verification, contact details, payment
   details, and training records outside the public repository; only the
   pseudonymous registry fields belong in the publishable evidence trail.
   Use `reviewer_attestation_template.json` and
   `reviewer_attestation_template.md` for the private consent, registration,
   conflict, blinding, no-identifier comment, and independent-judgement
   attestations that support those registry fields.
7. Review or regenerate the reviewer recruitment plan to confirm
   primary/secondary reviewer, adjudicator, privacy, and corpus-specialty
   familiarity targets:

```bash
python scripts/plan_reviewer_recruitment.py \
  --output-json validation_pack/reviewer_recruitment_plan.json \
  --output-md validation_pack/reviewer_recruitment_plan.md \
  --fail-on-incomplete
```

8. Review or regenerate the collection plan to confirm planned case,
   submission, reviewer-rating, calibration-pair, and stratum coverage:

```bash
python scripts/plan_validation_collection.py \
  --output-json validation_pack/collection_plan.json \
  --output-md validation_pack/collection_plan.md \
  --fail-on-underpowered
```

9. Preserve the pre-specified analysis contract in
   `statistical_analysis_plan.json` and `statistical_analysis_plan.md`. Evidence
   bundles hash this plan so judge-vs-clinician agreement is interpreted
   against public thresholds instead of post-hoc criteria.
10. Complete reviewer training using `reviewer_training_guide.json` and
   `reviewer_training_guide.md` before setting `training_completed=yes` in the
   pseudonymous registry. Keep named attendance records, signed attestations,
   and anchor-case discussion notes outside the public repository.
11. Use `independent_review_runbook.json` and
   `independent_review_runbook.md` as the coordinator checklist for private
   collection paths, command order, publishable outputs, and claim boundaries.
   The default private workspaces `reviewer_assignments/`,
   `private_review_inputs/`, and `private_review_runs/` are ignored by Git.
12. Publish the current validation-goal status so governance reviewers can see
   whether the repository is prepared, blocked, or claim-ready:

```bash
python scripts/summarize_validation_goal_status.py \
  --output-json validation_pack/validation_goal_status.json \
  --output-md validation_pack/validation_goal_status.md
```

13. Generate reviewer-specific assignment worksheets:

```bash
python scripts/build_reviewer_assignments.py \
  --reviewer-registry <reviewer_registry.csv> \
  --output-dir <reviewer_assignments_dir>
```

14. Audit the filled worksheet and reviewer registry before treating it as
   independent clinician evidence. The audit requires both overall note-quality
   ratings and complete required dimension ratings for each assigned
   case-submission:

```bash
python scripts/audit_clinician_review_readiness.py \
  --worksheet <filled_worksheet.csv> \
  --reviewer-registry <reviewer_registry.csv> \
  --output-json <readiness_report.json> \
  --output-md <readiness_report.md> \
  --fail-on-not-ready
```

15. Run Scribeval on the same blinded submissions.
16. Export Scribeval scores in the shape consumed by the calibration importer:

```bash
python scripts/export_validation_judge_scores.py \
  --output <scribeval_scores.json> \
  --dimensions omission,hallucination,medicolegal,ahpra,pdqi9,qnote
```

   The export contains IDs, scores, severities, judge metadata, and hashes. It
   intentionally omits transcript text, note text, raw judge responses,
   reasoning, and excerpts.

17. Summarise inter-rater reliability between clinician reviewers:

Before reliability and consensus analysis, publish an aggregate collection
status report if coordinators need to track whether assignments, completed
ratings, and Scribeval score exports are ready:

```bash
python scripts/summarize_validation_review_run.py \
  --reviewer-registry <reviewer_registry.csv> \
  --assignments-dir <reviewer_assignments_dir> \
  --worksheet <filled_worksheet.csv> \
  --judge-scores <scribeval_scores.json> \
  --output-json <review_run_status.json> \
  --output-md <review_run_status.md> \
  --fail-on-not-ready
```

The status report contains aggregate counts and issue counts only. It omits
reviewer IDs, reviewer comments, transcript text, candidate note text, raw judge
responses, reasoning, and excerpts.

```bash
python scripts/summarize_reviewer_reliability.py \
  --worksheet <filled_worksheet.csv> \
  --reviewer-registry <reviewer_registry.csv> \
  --output-json <reviewer_reliability.json> \
  --output-md <reviewer_reliability.md> \
  --fail-on-not-ready
```

   Low clinician reviewer agreement weakens judge-vs-clinician validation
   claims and should trigger rubric clarification, reviewer retraining, or
   adjudication.

18. Build consensus clinician ratings for judge-vs-consensus reporting:

```bash
python scripts/build_consensus_validation_ratings.py \
  --worksheet <filled_worksheet.csv> \
  --reviewer-registry <reviewer_registry.csv> \
  --judge-scores <scribeval_scores.json> \
  --output <consensus_calibration_pairs.json> \
  --output-summary-json <consensus_summary.json> \
  --output-summary-md <consensus_summary.md>
```

   Consensus ratings average qualified reviewer scores and use a consensus
   severity label. Rows with score or severity disagreement are flagged for
   adjudication before strong validation claims are made.

19. Build focused adjudication packets if consensus rows are disputed:

```bash
python scripts/build_adjudication_packets.py \
  --consensus-pairs <consensus_calibration_pairs.json> \
  --output-dir <adjudication_packets_dir>
```

   The adjudication worksheet and packets show only blinded submission labels,
   disputed dimensions, reviewer score ranges, and reviewer severity values.
   They omit reviewer IDs, source labels, prompt strategies, and seeded failure
   metadata.

20. Import adjudicator decisions back into consensus evidence:

```bash
python scripts/import_adjudication_decisions.py \
  --consensus-pairs <consensus_calibration_pairs.json> \
  --adjudication-worksheet <filled_adjudication_worksheet.csv> \
  --reviewer-registry <reviewer_registry.csv> \
  --adjudicator-id <adjudicator_reviewer_id> \
  --require-qualified-adjudicator \
  --output <adjudicated_consensus_calibration_pairs.json> \
  --output-summary-json <adjudicated_consensus_summary.json> \
  --output-summary-md <adjudicated_consensus_summary.md>
```

   This resolves disputed consensus rows only after a qualified adjudicator has
   supplied a complete score and severity decision.

21. Convert individual reviewer ratings and Scribeval scores into calibration pairs:

```bash
python scripts/import_validation_ratings.py \
  --worksheet validation_pack/evidence/synthetic_reviewer_worksheet_v0.csv \
  --judge-scores validation_pack/evidence/synthetic_scribeval_scores_v0.json \
  --output validation_pack/evidence/calibration_pairs_v0.json
```

Generate the stratified evidence summary:

```bash
python scripts/summarize_validation_evidence.py
```

For independent clinician ratings, add the registry checks:

```bash
python scripts/import_validation_ratings.py \
  --worksheet <filled_worksheet.csv> \
  --judge-scores <scribeval_scores.json> \
  --reviewer-registry <reviewer_registry.csv> \
  --require-qualified-reviewers \
  --output <calibration_pairs.json>
```

For a completed independent clinician review, the preferred reproducible path
is to build a versioned evidence bundle:

```bash
python scripts/build_validation_evidence_bundle.py \
  --run-id <review_run_id> \
  --worksheet <filled_worksheet.csv> \
  --reviewer-registry <reviewer_registry.csv> \
  --judge-scores <scribeval_scores.json> \
  --reviewer-assignments-dir <reviewer_assignments_dir> \
  --adjudicated-consensus-pairs <adjudicated_consensus_calibration_pairs.json> \
  --output-dir validation_pack/evidence_runs
```

The bundle includes the aggregate review-run status report, readiness report,
reviewer reliability report, individual and consensus calibration pairs,
agreement reports, stratified summary, validation-claim readiness assessment,
manifest, blinded reviewer-material hashes including the reviewer scoring guide,
adjudication-burden summary, source hashes, and the reviewer assignment manifest
hash when supplied. It does not copy reviewer-specific assignment worksheets
into the public bundle.

The committed `evidence_runs/synthetic_bootstrap_v1/` bundle is generated by
`python scripts/build_synthetic_evidence_bundle.py`. It demonstrates the full
evidence-run shape and audit trail with synthetic ratings only; it is not
independent clinical validation.

Audit generated evidence bundles before publishing or committing them:

```bash
python scripts/audit_validation_evidence_runs.py \
  --evidence-runs validation_pack/evidence_runs
```

22. Index generated evidence runs for public review:

```bash
python scripts/index_validation_evidence_runs.py \
  --evidence-runs validation_pack/evidence_runs \
  --output-json validation_pack/evidence_runs/index.json \
  --output-md validation_pack/evidence_runs/index.md
```

23. Assess whether the bundle is ready for validation claims:

```bash
python scripts/assess_validation_claim_readiness.py \
  --evidence-manifest validation_pack/evidence_runs/<review_run_id>/evidence_manifest.json \
  --output-json <validation_claim_readiness.json> \
  --output-md <validation_claim_readiness.md> \
  --fail-on-not-ready
```

24. Run:

```bash
scribeval calibrate validation_pack/evidence/calibration_pairs_v0.json
```

## Interpretation

Use agreement metrics as calibration evidence, not as a pass/fail device.

- Weighted kappa tests agreement on ordinal severity categories.
- ICC(2,1) tests absolute agreement on continuous 0-1 scores.
- Mean absolute difference shows the typical score gap between Scribeval and
  reviewers.
- The stratified evidence summary reports these agreement metrics by
  specialty, note source, prompt strategy, and safety-critical failure mode
  where enough pairs exist.

Review any dimension with low agreement before using it for procurement or
governance decisions. Common next steps are rubric tightening, clearer reviewer
instructions, more cases, or adjudication by a second clinician.

## Files

| File | Purpose |
|---|---|
| `case_manifest.json` | 20-case synthetic validation design |
| `clinician_review_protocol.json` | Minimum reviewer provenance and eligibility protocol |
| `collection_plan.json` / `collection_plan.md` | Planned reviewer-rating, calibration-pair, and stratum coverage |
| `statistical_analysis_plan.json` / `statistical_analysis_plan.md` | Pre-specified validation endpoints, thresholds, handling rules, and claim boundary |
| `validation_goal_status.json` / `validation_goal_status.md` | Current prepared/claim-ready status and blocking validation gaps |
| `independent_review_runbook.json` / `independent_review_runbook.md` | Coordinator workflow for private collection, public outputs, and claim boundaries |
| `reviewer_recruitment_plan.json` / `reviewer_recruitment_plan.md` | Reviewer panel, adjudicator, privacy, and corpus-specialty familiarity targets |
| `reviewer_attestation_template.json` / `reviewer_attestation_template.md` | Private reviewer consent, eligibility, blinding, and independence attestation template |
| `reviewer_training_guide.json` / `reviewer_training_guide.md` | Minimum reviewer training, anchor-case, and public-record requirements |
| `reviewer_intake_checklist.json` | Coordinator intake controls and public/private evidence boundaries |
| `reviewer_scoring_guide.md` | Clinician-facing score, severity, and dimension anchors |
| `reviewer_registry_template.csv` | Pseudonymous reviewer eligibility template |
| `reviewer_worksheet.csv` | Spreadsheet template for blinded human scoring |
| `corpus/` | Complete synthetic transcript/note case packets |
| `reviewer_packets/` | Generated clinician-facing blinded transcript/note packets |
| `reviewer_assignments/` | Ignored generated reviewer-specific assignment worksheets |
| `private_review_inputs/` / `private_review_runs/` | Ignored coordinator-only collection inputs and intermediate run files |
| `evidence/` | Worksheet, score, calibration-pair, and report evidence trail |
| `evidence/stratified_summary_v0.json` | Agreement coverage by specialty, source, prompt strategy, and failure mode |
| `evidence_runs/` | Optional generated independent clinician evidence bundles; do not commit raw reviewer CSV inputs |
| `evidence_runs/synthetic_bootstrap_v1/` | Committed synthetic workflow bundle for reproducibility testing |
| `results/example_calibration_pairs.json` | Example judge-vs-human calibration input |
| `results/example_calibration_report.md` | Example rendered interpretation |
