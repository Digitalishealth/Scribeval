# Sample Evaluation Cases

These are **entirely synthetic** consultation cases created for demonstration and testing purposes. **No real patient data is included.** All names, clinical details, and scenarios are fictional.

Each case contains deliberately planted errors in the `scribe_output.txt` to test specific evaluation dimensions:

| Case | Scenario | Planted Errors |
|------|----------|----------------|
| `case_gp_respiratory` | GP consultation for URTI | Penicillin allergy omitted; follow-up plan incomplete |
| `case_ed_chest_pain` | ED presentation with chest pain | ECG finding fabricated; red flag documentation missing |
| `case_psych_review` | Psychiatric review | Risk assessment incompletely captured; clinical reasoning simplified |
| `case_paeds_fever` | Paediatric febrile illness with otitis media | Weight-based dosing omitted; safety-netting red flags missing; allergy status not documented; review plan incomplete |
| `case_specialist_diabetes` | Endocrinology review of poorly controlled T2DM | Hypoglycaemia history hallucinated as absent; sulfonylurea cessation omitted; cardiology referral omitted; GLP-1 restart plan omitted; unwarranted metformin dose change fabricated |

## File Structure

Each case directory contains:
- `transcript.txt` — Simulated consultation transcript
- `scribe_output.txt` — AI scribe output with deliberate errors
- `reference_note.txt` — Clinician-authored reference note. It can be scored
  as a comparable submission, or supplied separately as optional adjudication
  context.

The directory also includes `benchmark_manifest.json`, which compares the
same two labels across all synthetic cases:

```bash
scribeval benchmark samples/benchmark_manifest.json \
    --dimensions omission,hallucination \
    --output samples_benchmark \
    --format both
```

## Ground-Truth Errors as a Benchmark

These cases are designed so that a competent evaluator **should** find the planted errors. They act as a minimal regression benchmark: if Scribeval (or any scribe evaluator) fails to flag the hallucinated hypoglycaemia status in `case_specialist_diabetes`, that is a concrete failure to investigate.

For a programmatic benchmark that doesn't rely on human-curated cases, see the `scribeval verify-detection` command, which injects deterministic errors into any clean note and measures recall.
