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
2. Build a packet for each case with the transcript and blinded candidate
   notes.
3. Give reviewers `reviewer_worksheet.csv` or import it into a spreadsheet.
4. Ask reviewers to score each blinded submission against the transcript, not
   against another note.
5. Run Scribeval on the same blinded submissions.
6. Convert reviewer ratings and Scribeval scores into the JSON shape shown in
   `results/example_calibration_pairs.json`.
7. Run:

```bash
scribeval calibrate validation_pack/results/example_calibration_pairs.json
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
| `reviewer_worksheet.csv` | Spreadsheet template for blinded human scoring |
| `results/example_calibration_pairs.json` | Example judge-vs-human calibration input |
| `results/example_calibration_report.md` | Example rendered interpretation |

