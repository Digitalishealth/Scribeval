# Sample Evaluation Cases

These are **entirely synthetic** consultation cases created for demonstration and testing purposes. **No real patient data is included.** All names, clinical details, and scenarios are fictional.

Each case contains deliberately planted errors in the `scribe_output.txt` to test specific evaluation dimensions:

| Case | Scenario | Planted Errors |
|------|----------|----------------|
| `case_gp_respiratory` | GP consultation for URTI | Penicillin allergy omitted; follow-up plan incomplete |
| `case_ed_chest_pain` | ED presentation with chest pain | ECG finding fabricated; red flag documentation missing |
| `case_psych_review` | Psychiatric review | Risk assessment incompletely captured; clinical reasoning simplified |

## File Structure

Each case directory contains:
- `transcript.txt` — Simulated consultation transcript
- `scribe_output.txt` — AI scribe output with deliberate errors
- `reference_note.txt` — Gold-standard clinician note for comparison
