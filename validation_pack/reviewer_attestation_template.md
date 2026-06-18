# Reviewer Attestation Template

This template defines the private reviewer attestation record coordinators must
complete before accepting independent clinician ratings into a Scribeval
validation evidence run.

Benchmark unit: `whole transcript -> final note quality score`

## Private Record Policy

Completed attestations must stay outside the public repository. The public
evidence trail stores only the pseudonymous reviewer registry fields:

- `reviewer_id`
- `profession`
- `country`
- `registration_status`
- `years_post_registration`
- `specialty`
- `review_role`
- `conflict_of_interest`
- `training_completed`

Do not publish reviewer names, contact details, registration numbers,
registration verification source documents, signed consent records,
attestation signatures, attestation dates, or coordinator names.

## Required Attestations

| Attestation | Private Evidence |
|---|---|
| participation and publication consent | signed consent retained by coordinator |
| current registration verified | source registration check retained by coordinator |
| minimum experience confirmed | years post registration recorded in pseudonymous registry |
| conflict of interest none | conflict declaration retained by coordinator |
| training completed before scoring | training and anchor-case completion retained by coordinator |
| blinding understood | reviewer confirms candidate source and prompt strategy are hidden |
| no identifier comment policy understood | reviewer confirms comments must not include direct identifiers |
| independent judgement confirmed | reviewer confirms ratings use the transcript plus blinded final note only |
| adjudication escalation understood | reviewer confirms disputed scoring follows the adjudication workflow |

Set `training_completed=yes` and `conflict_of_interest=none` in the
pseudonymous registry only after every required attestation is complete and
retained privately.

## Claim Boundary

A completed reviewer attestation supports reviewer provenance and governance
only. It is not itself validation evidence; validation claims require completed
independent clinician ratings, reliability analysis, adjudicated consensus, and
claim-readiness checks.
