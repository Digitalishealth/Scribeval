# Scribeval Statistical Analysis Plan

This plan pre-specifies how independent clinician ratings will be compared with
Scribeval transcript-to-note scores before any validation claim is made.

Benchmark unit: `whole transcript -> final note quality score`

## Analysis Population

Include every blinded case-submission with complete required clinician ratings,
exported Scribeval judge scores, and qualified reviewer provenance.

Exclude:

- case-submissions missing any required dimension rating
- case-submissions without the required overall note-quality rating
- ratings from reviewers who fail eligibility, conflict, or training checks
- consensus rows with unresolved `adjudication_required=true`

The unit of analysis is:

```text
case transcript + blinded final note + dimension
```

## Primary Endpoints

| Endpoint | Metric | Target | Threshold |
|---|---|---|---:|
| judge-vs-clinician consensus agreement | Cohen weighted kappa | Scribeval severity rating versus adjudicated clinician consensus severity | >= 0.6 |
| clinician reviewer reliability | Cohen weighted kappa | independent clinician reviewer severity agreement | >= 0.6 |

Primary dimensions:

- omission
- hallucination
- medicolegal
- AHPRA
- PDQI-9
- QNOTE
- overall note quality

## Secondary Endpoints

- ICC(2,1) absolute agreement between 0-1 Scribeval scores and clinician
  consensus scores
- mean absolute score difference
- exact severity agreement
- adjudication burden by dimension and stratum

## Required Strata

Agreement must be reported by:

- specialty
- note source
- prompt strategy
- safety-critical failure mode

Each stratum value must have at least two calibration pairs before it can support
the validation-claim readiness check.

## Minimum Coverage

| Requirement | Threshold |
|---|---:|
| Cases | 20 |
| Submissions | 100 |
| Qualified reviewers | 2 |
| Reviewers per case-submission | 2 |
| Minimum pairs per stratum value | 2 |
| Unresolved adjudication-required rows | 0 |

## Handling Rules

- Do not impute missing clinician ratings.
- Exclude incomplete units from calibration pairs and fail readiness when
  required coverage is incomplete.
- Build consensus ratings from qualified reviewers.
- Resolve score or severity disagreement through qualified adjudication before
  validation claims.
- If multiple Scribeval runs are used, analyze exported aggregate judge scores
  and retain run metadata in the judge-score export.
- Report AMT medication terminology as an optional secondary dimension when it
  is collected; it is not required for the primary validation claim.

## Sensitivity Analyses

- Report agreement by specialty, note source, prompt strategy, and
  safety-critical failure mode.
- Inspect dimensions with low kappa or high mean absolute difference before
  governance or procurement use.
- Repeat interpretation excluding optional AMT medication terminology when it is
  not collected.
- Review adjudication burden by stratum to identify ambiguous rubric
  instructions or clinically contentious cases.

## Claim Boundary

This statistical analysis plan is not validation evidence. It defines how a
completed independent clinician evidence bundle will be interpreted and should
be hashed into the evidence trail before public claims are made.
