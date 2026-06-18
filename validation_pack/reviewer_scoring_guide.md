# Scribeval Clinician Reviewer Scoring Guide

This guide standardises how independent clinicians score blinded final notes
against the whole consultation transcript. Use it with the reviewer packets and
worksheet generated from the validation corpus.

## Review Unit

Score each blinded final note against the whole transcript:

```text
whole transcript -> final note quality score
```

Do not score a note against another note. Do not infer quality from submission
order. A GP-written note, Nurse + CDSS note, model-generated note, or scribe
product note should all be scored by the same rules when presented as a blinded
submission.

## Score Scale

Use the 0-1 score as a quality score where `1.00` means the note is fully
acceptable for the dimension and `0.00` means it fails the dimension.

| Score range | Interpretation |
|---|---|
| `0.90-1.00` | Excellent or clinically acceptable with at most trivial issues |
| `0.75-0.89` | Mostly acceptable with minor gaps unlikely to change care |
| `0.50-0.74` | Material quality problem requiring review or correction |
| `0.25-0.49` | Serious problem that could affect care, governance, or safety |
| `0.00-0.24` | Critical failure or unusable documentation for that dimension |

## Severity Scale

Choose the severity that best represents the worst clinically meaningful issue
for the dimension.

| Severity | Meaning |
|---|---|
| `none` | No meaningful issue identified |
| `low` | Minor wording, structure, or detail issue |
| `moderate` | Clinically relevant gap or overstatement needing correction |
| `high` | Significant safety, legal, or continuity-of-care risk |
| `critical` | Immediate or serious risk, fabricated key fact, or unsafe omission |

## Required Ratings

Each assigned case-submission needs:

- overall note quality
- omission
- hallucination
- medicolegal adequacy
- AHPRA compliance
- PDQI-9
- QNOTE

Medication terminology is optional unless the protocol for the run explicitly
turns it on.

## Dimension Anchors

Overall note quality: judge whether the final note is fit for its intended
clinical documentation purpose after considering safety, accuracy, usefulness,
clarity, and follow-up.

Omission: penalise clinically important transcript information that is missing
from the note, especially red flags, medications/allergies, escalation advice,
follow-up ownership, and safety-netting.

Hallucination: penalise unsupported or fabricated information. A confident
statement not grounded in the transcript is worse than a cautious uncertainty.

Medicolegal adequacy: judge whether the note supports continuity of care,
reasonable clinical decision-making, safety-netting, consent/refusal where
relevant, and follow-up accountability.

AHPRA compliance: judge whether the note is professionally appropriate,
truthful, respectful, culturally safe, and avoids misleading claims or
inappropriate certainty.

PDQI-9: judge whether the note is up-to-date, accurate, thorough, useful,
organised, comprehensible, succinct, synthesised, and internally consistent.

QNOTE: judge the core clinical note domains, especially presenting issue,
history, relevant background, medications/allergies, assessment, plan, and
overall impression.

Medication terminology: when enabled, judge whether medication names and
terminology are valid and unambiguous, with particular attention to fabricated
or unsafe medication details.

## Comment Guidance

Reviewer comments are optional but useful for adjudication. Do not include
patient identifiers, clinician identifiers, reviewer names, provider numbers,
registration numbers, email addresses, or phone numbers in reviewer comments.
