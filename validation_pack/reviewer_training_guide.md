# Clinician Reviewer Training Guide

This guide defines the minimum reviewer training and anchoring requirements
before clinician ratings are accepted into a Scribeval validation evidence
bundle.

Benchmark unit: `whole transcript -> final note quality score`

## Required Materials

- `reviewer_scoring_guide.md`
- `reviewer_intake_checklist.json`
- `statistical_analysis_plan.json`
- `reviewer_packets/README.md`

## Learning Objectives

Reviewers must be able to:

- score each final note against the whole consultation transcript rather than
  another note
- apply the 0-1 score scale and ordered severity scale consistently across all
  candidate note sources
- identify clinically significant omissions, unsupported hallucinations,
  medicolegal gaps, AHPRA concerns, PDQI-9 quality issues, and QNOTE domain gaps
- preserve blinding by ignoring submission order and avoiding source or
  prompt-strategy inference
- avoid direct patient, clinician, reviewer, provider, registration, phone, and
  email identifiers in reviewer comments
- escalate ambiguous or disputed ratings through the adjudication workflow
  rather than changing the protocol ad hoc

## Required Training Steps

| Step | Evidence |
|---|---|
| read scoring guide | reviewer attests that the scoring guide was read before scoring |
| review score and severity anchors | reviewer attests that score bands and severity labels are understood |
| complete anchor-case discussion | coordinator records completion outside the public repository |
| confirm blinding and comment policy | reviewer attests to blinding and no-identifier comment rules |
| confirm conflict and eligibility screening | pseudonymous registry has current registration, no conflict, and `training_completed=yes` |

## Anchor Cases

Before independent scoring, complete at least two anchor-case discussions.

The anchor discussion must include:

- omission
- hallucination
- medicolegal adequacy
- AHPRA
- PDQI-9
- QNOTE
- overall note quality

It should include examples of:

- clinically significant omission
- unsupported hallucination
- medicolegal follow-up gap

The reviewer may proceed to independent scoring only after the coordinator
confirms the anchor-case discussion and training attestation.

## Public Record Policy

The public evidence trail stores only the pseudonymous `reviewer_id` and the
`training_completed` flag. Named attendance records, signed training
attestations, source registration verification, and anchor-case discussion notes
must stay outside the public repository.

## Claim Boundary

Training completion improves reviewer consistency but is not itself validation
evidence. Validation claims still require qualified independent clinician
ratings, reviewer reliability, adjudicated consensus, and claim-readiness
checks.
