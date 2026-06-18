# Clinician Reviewer Reliability Report

Reviewer reliability describes agreement between clinician reviewers. Low reviewer reliability weakens judge-vs-clinician validation claims and should trigger rubric clarification, reviewer retraining, or adjudication before procurement or governance use.

## Coverage

- Readiness status: ready
- Cases: 20
- Submissions: 100
- Reviewer pairs: 1
- Reliability pairs: 700
- Dimensions: omission, hallucination, medicolegal, ahpra, pdqi9, qnote, overall

## Dimension Agreement

| Dimension | N | Weighted kappa | Kappa interpretation | ICC(2,1) | Mean abs diff |
|---|---:|---:|---|---:|---:|
| ahpra | 100 | 0.949 | almost perfect | 0.995 | 0.020 |
| hallucination | 100 | 0.935 | almost perfect | 0.995 | 0.020 |
| medicolegal | 100 | 0.911 | almost perfect | 0.995 | 0.020 |
| omission | 100 | 0.979 | almost perfect | 0.992 | 0.020 |
| overall | 100 | 0.827 | almost perfect | 0.992 | 0.020 |
| pdqi9 | 100 | 1.000 | almost perfect | 0.991 | 0.020 |
| qnote | 100 | 0.989 | almost perfect | 0.992 | 0.020 |

## Specialty

| Value | Cases | Submissions | Reviewer pairs | Pairs | Dimensions | Mean abs diff | Severity exact agreement |
|---|---:|---:|---:|---:|---:|---:|---:|
| aged_care | 2 | 10 | 1 | 70 | 7 | 0.020 | 0.943 |
| chronic_disease | 2 | 10 | 1 | 70 | 7 | 0.020 | 0.900 |
| general_practice | 9 | 45 | 1 | 315 | 7 | 0.020 | 0.946 |
| mental_health | 1 | 5 | 1 | 35 | 7 | 0.020 | 0.971 |
| paediatrics | 2 | 10 | 1 | 70 | 7 | 0.020 | 0.886 |
| palliative_care | 1 | 5 | 1 | 35 | 7 | 0.020 | 0.886 |
| telehealth | 1 | 5 | 1 | 35 | 7 | 0.020 | 0.886 |
| urgent_care | 2 | 10 | 1 | 70 | 7 | 0.020 | 0.971 |

## Note Source

| Value | Cases | Submissions | Reviewer pairs | Pairs | Dimensions | Mean abs diff | Severity exact agreement |
|---|---:|---:|---:|---:|---:|---:|---:|
| model_candidate | 20 | 80 | 1 | 560 | 7 | 0.020 | 0.916 |
| nurse_cdss | 20 | 20 | 1 | 140 | 7 | 0.020 | 1.000 |

## Prompt Strategy

| Value | Cases | Submissions | Reviewer pairs | Pairs | Dimensions | Mean abs diff | Severity exact agreement |
|---|---:|---:|---:|---:|---:|---:|---:|
| cdss_checklist | 20 | 20 | 1 | 140 | 7 | 0.020 | 1.000 |
| cdss_informed | 20 | 20 | 1 | 140 | 7 | 0.020 | 0.957 |
| safety_first | 20 | 20 | 1 | 140 | 7 | 0.020 | 0.857 |
| standard | 20 | 20 | 1 | 140 | 7 | 0.020 | 0.886 |
| structured_soap | 20 | 20 | 1 | 140 | 7 | 0.020 | 0.964 |

## Failure Mode

| Value | Cases | Submissions | Reviewer pairs | Pairs | Dimensions | Mean abs diff | Severity exact agreement |
|---|---:|---:|---:|---:|---:|---:|---:|
| anticoagulant_head_injury_escalation_gap | 1 | 5 | 1 | 35 | 7 | 0.020 | 0.943 |
| asthma_action_plan_gap | 1 | 5 | 1 | 35 | 7 | 0.020 | 0.886 |
| clinically_significant_omission | 18 | 90 | 1 | 630 | 7 | 0.020 | 0.938 |
| confidentiality_documentation_gap | 1 | 5 | 1 | 35 | 7 | 0.020 | 0.943 |
| contraception_contraindication_gap | 1 | 5 | 1 | 35 | 7 | 0.020 | 0.943 |
| copd_escalation_gap | 1 | 5 | 1 | 35 | 7 | 0.020 | 0.971 |
| culturally_safe_care_gap | 1 | 5 | 1 | 35 | 7 | 0.020 | 0.914 |
| delirium_escalation_gap | 1 | 5 | 1 | 35 | 7 | 0.020 | 0.943 |
| diabetes_safety_net_gap | 1 | 5 | 1 | 35 | 7 | 0.020 | 0.886 |
| documentation_photo_gap | 1 | 5 | 1 | 35 | 7 | 0.020 | 0.971 |
| ectopic_pregnancy_escalation_gap | 1 | 5 | 1 | 35 | 7 | 0.020 | 0.943 |
| medication_adherence_gap | 1 | 5 | 1 | 35 | 7 | 0.020 | 0.886 |
| medication_dosing_risk | 5 | 25 | 1 | 175 | 7 | 0.020 | 0.909 |
| medicolegal_followup_gap | 9 | 29 | 1 | 203 | 7 | 0.020 | 0.946 |
| opioid_safety_net_gap | 1 | 5 | 1 | 35 | 7 | 0.020 | 0.886 |
| over_inference_from_uncertain_transcript | 2 | 10 | 1 | 70 | 7 | 0.020 | 0.943 |
| preventive_care_followup_gap | 1 | 5 | 1 | 35 | 7 | 0.020 | 0.914 |
| renal_medication_interaction | 1 | 5 | 1 | 35 | 7 | 0.020 | 0.914 |
| results_followup_ownership_gap | 1 | 5 | 1 | 35 | 7 | 0.020 | 0.914 |
| skin_cancer_referral_gap | 1 | 5 | 1 | 35 | 7 | 0.020 | 0.971 |
| suicide_risk_documentation_gap | 1 | 5 | 1 | 35 | 7 | 0.020 | 0.971 |
| unsupported_hallucination | 11 | 39 | 1 | 273 | 7 | 0.020 | 0.949 |
| withdrawal_risk_gap | 1 | 5 | 1 | 35 | 7 | 0.020 | 0.943 |
| work_certificate_documentation_gap | 1 | 5 | 1 | 35 | 7 | 0.020 | 1.000 |
