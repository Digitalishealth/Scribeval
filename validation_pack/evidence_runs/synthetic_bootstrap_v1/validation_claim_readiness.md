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
| stratum_pair_count.specialty.aged_care | pass | 140 | >= 2 |
| stratum_pair_count.specialty.chronic_disease | pass | 140 | >= 2 |
| stratum_pair_count.specialty.general_practice | pass | 630 | >= 2 |
| stratum_pair_count.specialty.mental_health | pass | 70 | >= 2 |
| stratum_pair_count.specialty.paediatrics | pass | 140 | >= 2 |
| stratum_pair_count.specialty.palliative_care | pass | 70 | >= 2 |
| stratum_pair_count.specialty.telehealth | pass | 70 | >= 2 |
| stratum_pair_count.specialty.urgent_care | pass | 140 | >= 2 |
| stratum.note_source | pass | 2 | > 0 rows |
| stratum_pair_count.note_source.model_candidate | pass | 1120 | >= 2 |
| stratum_pair_count.note_source.nurse_cdss | pass | 280 | >= 2 |
| stratum.prompt_strategy | pass | 5 | > 0 rows |
| stratum_pair_count.prompt_strategy.cdss_checklist | pass | 280 | >= 2 |
| stratum_pair_count.prompt_strategy.cdss_informed | pass | 280 | >= 2 |
| stratum_pair_count.prompt_strategy.safety_first | pass | 280 | >= 2 |
| stratum_pair_count.prompt_strategy.standard | pass | 280 | >= 2 |
| stratum_pair_count.prompt_strategy.structured_soap | pass | 280 | >= 2 |
| stratum.failure_mode | pass | 24 | > 0 rows |
| stratum_pair_count.failure_mode.anticoagulant_head_injury_escalation_gap | pass | 70 | >= 2 |
| stratum_pair_count.failure_mode.asthma_action_plan_gap | pass | 70 | >= 2 |
| stratum_pair_count.failure_mode.clinically_significant_omission | pass | 1260 | >= 2 |
| stratum_pair_count.failure_mode.confidentiality_documentation_gap | pass | 70 | >= 2 |
| stratum_pair_count.failure_mode.contraception_contraindication_gap | pass | 70 | >= 2 |
| stratum_pair_count.failure_mode.copd_escalation_gap | pass | 70 | >= 2 |
| stratum_pair_count.failure_mode.culturally_safe_care_gap | pass | 70 | >= 2 |
| stratum_pair_count.failure_mode.delirium_escalation_gap | pass | 70 | >= 2 |
| stratum_pair_count.failure_mode.diabetes_safety_net_gap | pass | 70 | >= 2 |
| stratum_pair_count.failure_mode.documentation_photo_gap | pass | 70 | >= 2 |
| stratum_pair_count.failure_mode.ectopic_pregnancy_escalation_gap | pass | 70 | >= 2 |
| stratum_pair_count.failure_mode.medication_adherence_gap | pass | 70 | >= 2 |
| stratum_pair_count.failure_mode.medication_dosing_risk | pass | 350 | >= 2 |
| stratum_pair_count.failure_mode.medicolegal_followup_gap | pass | 406 | >= 2 |
| stratum_pair_count.failure_mode.opioid_safety_net_gap | pass | 70 | >= 2 |
| stratum_pair_count.failure_mode.over_inference_from_uncertain_transcript | pass | 140 | >= 2 |
| stratum_pair_count.failure_mode.preventive_care_followup_gap | pass | 70 | >= 2 |
| stratum_pair_count.failure_mode.renal_medication_interaction | pass | 70 | >= 2 |
| stratum_pair_count.failure_mode.results_followup_ownership_gap | pass | 70 | >= 2 |
| stratum_pair_count.failure_mode.skin_cancer_referral_gap | pass | 70 | >= 2 |
| stratum_pair_count.failure_mode.suicide_risk_documentation_gap | pass | 70 | >= 2 |
| stratum_pair_count.failure_mode.unsupported_hallucination | pass | 546 | >= 2 |
| stratum_pair_count.failure_mode.withdrawal_risk_gap | pass | 70 | >= 2 |
| stratum_pair_count.failure_mode.work_certificate_documentation_gap | pass | 70 | >= 2 |
