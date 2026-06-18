# Validation Collection Plan

This plan describes expected collection coverage before clinician ratings are gathered. It is not validation evidence; it defines the rating volume and stratum coverage needed for the later evidence bundle.

Benchmark unit: `whole transcript -> final note quality score`

## Planned Coverage

- Cases: 20
- Case-submissions: 100
- Reviewers per case-submission: 2
- Required dimension ratings: 1200
- Overall ratings: 200
- Individual calibration pairs: 1400
- Consensus pairs: 700

## Strata

### Specialty

| Value | Cases | Case-submissions | Reviewer rows | Individual pairs | Consensus pairs | Meets threshold |
|---|---:|---:|---:|---:|---:|---|
| aged_care | 2 | 10 | 20 | 140 | 70 | yes |
| chronic_disease | 2 | 10 | 20 | 140 | 70 | yes |
| general_practice | 9 | 45 | 90 | 630 | 315 | yes |
| mental_health | 1 | 5 | 10 | 70 | 35 | yes |
| paediatrics | 2 | 10 | 20 | 140 | 70 | yes |
| palliative_care | 1 | 5 | 10 | 70 | 35 | yes |
| telehealth | 1 | 5 | 10 | 70 | 35 | yes |
| urgent_care | 2 | 10 | 20 | 140 | 70 | yes |

### Note Source

| Value | Cases | Case-submissions | Reviewer rows | Individual pairs | Consensus pairs | Meets threshold |
|---|---:|---:|---:|---:|---:|---|
| model_candidate | 20 | 80 | 160 | 1120 | 560 | yes |
| nurse_cdss | 20 | 20 | 40 | 280 | 140 | yes |

### Prompt Strategy

| Value | Cases | Case-submissions | Reviewer rows | Individual pairs | Consensus pairs | Meets threshold |
|---|---:|---:|---:|---:|---:|---|
| cdss_checklist | 20 | 20 | 40 | 280 | 140 | yes |
| cdss_informed | 20 | 20 | 40 | 280 | 140 | yes |
| safety_first | 20 | 20 | 40 | 280 | 140 | yes |
| standard | 20 | 20 | 40 | 280 | 140 | yes |
| structured_soap | 20 | 20 | 40 | 280 | 140 | yes |

### Failure Mode

| Value | Cases | Case-submissions | Reviewer rows | Individual pairs | Consensus pairs | Meets threshold |
|---|---:|---:|---:|---:|---:|---|
| anticoagulant_head_injury_escalation_gap | 1 | 5 | 10 | 70 | 35 | yes |
| asthma_action_plan_gap | 1 | 5 | 10 | 70 | 35 | yes |
| clinically_significant_omission | 18 | 90 | 180 | 1260 | 630 | yes |
| confidentiality_documentation_gap | 1 | 5 | 10 | 70 | 35 | yes |
| contraception_contraindication_gap | 1 | 5 | 10 | 70 | 35 | yes |
| copd_escalation_gap | 1 | 5 | 10 | 70 | 35 | yes |
| culturally_safe_care_gap | 1 | 5 | 10 | 70 | 35 | yes |
| delirium_escalation_gap | 1 | 5 | 10 | 70 | 35 | yes |
| diabetes_safety_net_gap | 1 | 5 | 10 | 70 | 35 | yes |
| documentation_photo_gap | 1 | 5 | 10 | 70 | 35 | yes |
| ectopic_pregnancy_escalation_gap | 1 | 5 | 10 | 70 | 35 | yes |
| medication_adherence_gap | 1 | 5 | 10 | 70 | 35 | yes |
| medication_dosing_risk | 5 | 25 | 50 | 350 | 175 | yes |
| medicolegal_followup_gap | 9 | 29 | 58 | 406 | 203 | yes |
| opioid_safety_net_gap | 1 | 5 | 10 | 70 | 35 | yes |
| over_inference_from_uncertain_transcript | 2 | 10 | 20 | 140 | 70 | yes |
| preventive_care_followup_gap | 1 | 5 | 10 | 70 | 35 | yes |
| renal_medication_interaction | 1 | 5 | 10 | 70 | 35 | yes |
| results_followup_ownership_gap | 1 | 5 | 10 | 70 | 35 | yes |
| skin_cancer_referral_gap | 1 | 5 | 10 | 70 | 35 | yes |
| suicide_risk_documentation_gap | 1 | 5 | 10 | 70 | 35 | yes |
| unsupported_hallucination | 11 | 39 | 78 | 546 | 273 | yes |
| withdrawal_risk_gap | 1 | 5 | 10 | 70 | 35 | yes |
| work_certificate_documentation_gap | 1 | 5 | 10 | 70 | 35 | yes |

## Underpowered Stratum Values

None.
