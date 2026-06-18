# Validation Claim Readiness

Status: not ready

A structurally valid evidence bundle is not automatically strong enough for validation claims. This assessment requires completed independent clinician review, reliable clinician agreement, judge-vs-consensus agreement across required dimensions, full corpus coverage, and no unresolved adjudication flags.

## Coverage

- Cases: 20
- Submissions: 100
- Consensus pairs: 700
- Individual calibration pairs: 1400
- Reviewer reliability pairs: 700
- Adjudication required: 47

## Checks

| Check | Status | Observed | Threshold |
|---|---|---:|---:|
| benchmark_unit | pass | whole transcript -> final note quality score | whole transcript -> final note quality score |
| evidence_status | fail | synthetic_bootstrap | independent_clinician_review |
| review_readiness | pass | True | True |
| case_count | pass | 20 | >= 20 |
| submission_count | pass | 100 | >= 100 |
| qualified_reviewer_count | pass | 2 | >= 2 |
| complete_case_submission_count | pass | 100 | 100 |
| consensus_adjudication_required_count | fail | 47 | <= 0 |
| reviewer_reliability.omission | pass | 0.9787 | >= 0.6 |
| reviewer_reliability.hallucination | pass | 0.935 | >= 0.6 |
| reviewer_reliability.medicolegal | pass | 0.9108 | >= 0.6 |
| reviewer_reliability.ahpra | pass | 0.9485 | >= 0.6 |
| reviewer_reliability.pdqi9 | pass | 1.0 | >= 0.6 |
| reviewer_reliability.qnote | pass | 0.9885 | >= 0.6 |
| reviewer_reliability.overall | pass | 0.8266 | >= 0.6 |
| consensus_agreement.omission | pass | 0.9787 | >= 0.6 |
| consensus_agreement.hallucination | pass | 1.0 | >= 0.6 |
| consensus_agreement.medicolegal | pass | 0.9108 | >= 0.6 |
| consensus_agreement.ahpra | pass | 1.0 | >= 0.6 |
| consensus_agreement.pdqi9 | pass | 1.0 | >= 0.6 |
| consensus_agreement.qnote | pass | 0.9885 | >= 0.6 |
| consensus_agreement.overall | pass | 0.8266 | >= 0.6 |
| stratum.specialty | pass | 8 | > 0 rows |
| stratum.note_source | pass | 2 | > 0 rows |
| stratum.prompt_strategy | pass | 5 | > 0 rows |
| stratum.failure_mode | pass | 24 | > 0 rows |
