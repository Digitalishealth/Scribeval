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

3. Give reviewers `reviewer_packets/`, plus `reviewer_worksheet.csv` or an
   imported spreadsheet copy.
4. Ask reviewers to score each blinded submission against the transcript, not
   against another note.
5. Assign each reviewer a pseudonymous `reviewer_id` and record eligibility in
   `reviewer_registry_template.csv`. Do not store names, contact details,
   provider numbers, or registration numbers in this public evidence trail.
6. Run Scribeval on the same blinded submissions.
7. Export Scribeval scores in the shape shown in
   `evidence/synthetic_scribeval_scores_v0.json`.
8. Convert reviewer ratings and Scribeval scores into calibration pairs:

```bash
python scripts/import_validation_ratings.py \
  --worksheet validation_pack/evidence/synthetic_reviewer_worksheet_v0.csv \
  --judge-scores validation_pack/evidence/synthetic_scribeval_scores_v0.json \
  --output validation_pack/evidence/calibration_pairs_v0.json
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

9. Run:

```bash
scribeval calibrate validation_pack/evidence/calibration_pairs_v0.json
```

## Interpretation

Use agreement metrics as calibration evidence, not as a pass/fail device.

- Weighted kappa tests agreement on ordinal severity categories.
- ICC(2,1) tests absolute agreement on continuous 0-1 scores.
- Mean absolute difference shows the typical score gap between Scribeval and
  reviewers.

Review any dimension with low agreement before using it for procurement or
governance decisions. Common next steps are rubric tightening, clearer reviewer
instructions, more cases, or adjudication by a second clinician.

## Files

| File | Purpose |
|---|---|
| `case_manifest.json` | 20-case synthetic validation design |
| `clinician_review_protocol.json` | Minimum reviewer provenance and eligibility protocol |
| `reviewer_registry_template.csv` | Pseudonymous reviewer eligibility template |
| `reviewer_worksheet.csv` | Spreadsheet template for blinded human scoring |
| `corpus/` | Complete synthetic transcript/note case packets |
| `reviewer_packets/` | Generated clinician-facing blinded transcript/note packets |
| `evidence/` | Worksheet, score, calibration-pair, and report evidence trail |
| `results/example_calibration_pairs.json` | Example judge-vs-human calibration input |
| `results/example_calibration_report.md` | Example rendered interpretation |
