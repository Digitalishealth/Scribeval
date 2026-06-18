# Adjudication Burden Summary

This report summarizes unresolved consensus-rating disagreements that need
qualified adjudicator review before strong validation claims.

This summary contains aggregate adjudication counts only. It excludes reviewer identifiers, reviewer comments, transcript text, and candidate note text.

## Coverage

- Consensus pairs: 700
- Adjudication required: 47
- Adjudication required rate: 0.067
- Mean reviewer score range when required: 0.020

## Dimension

| Value | Cases | Submissions | Consensus pairs | Required | Required rate | Mean score range | Severity gaps |
|---|---:|---:|---:|---:|---:|---:|---|
| ahpra | 20 | 100 | 100 | 7 | 0.070 | 0.020 | 1: 7 |
| hallucination | 20 | 100 | 100 | 9 | 0.090 | 0.020 | 1: 9 |
| medicolegal | 20 | 100 | 100 | 12 | 0.120 | 0.020 | 1: 12 |
| omission | 20 | 100 | 100 | 2 | 0.020 | 0.020 | 1: 2 |
| overall | 20 | 100 | 100 | 16 | 0.160 | 0.020 | 1: 16 |
| pdqi9 | 20 | 100 | 100 | 0 | 0.000 | 0.000 | none |
| qnote | 20 | 100 | 100 | 1 | 0.010 | 0.020 | 1: 1 |

## Specialty

| Value | Cases | Submissions | Consensus pairs | Required | Required rate | Mean score range | Severity gaps |
|---|---:|---:|---:|---:|---:|---:|---|
| aged_care | 2 | 10 | 70 | 4 | 0.057 | 0.020 | 1: 4 |
| chronic_disease | 2 | 10 | 70 | 7 | 0.100 | 0.020 | 1: 7 |
| general_practice | 9 | 45 | 315 | 17 | 0.054 | 0.020 | 1: 17 |
| mental_health | 1 | 5 | 35 | 1 | 0.029 | 0.020 | 1: 1 |
| paediatrics | 2 | 10 | 70 | 8 | 0.114 | 0.020 | 1: 8 |
| palliative_care | 1 | 5 | 35 | 4 | 0.114 | 0.020 | 1: 4 |
| telehealth | 1 | 5 | 35 | 4 | 0.114 | 0.020 | 1: 4 |
| urgent_care | 2 | 10 | 70 | 2 | 0.029 | 0.020 | 1: 2 |

## Note Source

| Value | Cases | Submissions | Consensus pairs | Required | Required rate | Mean score range | Severity gaps |
|---|---:|---:|---:|---:|---:|---:|---|
| model_candidate | 20 | 80 | 560 | 47 | 0.084 | 0.020 | 1: 47 |
| nurse_cdss | 20 | 20 | 140 | 0 | 0.000 | 0.000 | none |

## Prompt Strategy

| Value | Cases | Submissions | Consensus pairs | Required | Required rate | Mean score range | Severity gaps |
|---|---:|---:|---:|---:|---:|---:|---|
| cdss_checklist | 20 | 20 | 140 | 0 | 0.000 | 0.000 | none |
| cdss_informed | 20 | 20 | 140 | 6 | 0.043 | 0.020 | 1: 6 |
| safety_first | 20 | 20 | 140 | 20 | 0.143 | 0.020 | 1: 20 |
| standard | 20 | 20 | 140 | 16 | 0.114 | 0.020 | 1: 16 |
| structured_soap | 20 | 20 | 140 | 5 | 0.036 | 0.020 | 1: 5 |

## Failure Mode

| Value | Cases | Submissions | Consensus pairs | Required | Required rate | Mean score range | Severity gaps |
|---|---:|---:|---:|---:|---:|---:|---|
| anticoagulant_head_injury_escalation_gap | 1 | 5 | 35 | 2 | 0.057 | 0.020 | 1: 2 |
| asthma_action_plan_gap | 1 | 5 | 35 | 4 | 0.114 | 0.020 | 1: 4 |
| clinically_significant_omission | 18 | 90 | 630 | 39 | 0.062 | 0.020 | 1: 39 |
| confidentiality_documentation_gap | 1 | 5 | 35 | 2 | 0.057 | 0.020 | 1: 2 |
| contraception_contraindication_gap | 1 | 5 | 35 | 2 | 0.057 | 0.020 | 1: 2 |
| copd_escalation_gap | 1 | 5 | 35 | 1 | 0.029 | 0.020 | 1: 1 |
| culturally_safe_care_gap | 1 | 5 | 35 | 3 | 0.086 | 0.020 | 1: 3 |
| delirium_escalation_gap | 1 | 5 | 35 | 2 | 0.057 | 0.020 | 1: 2 |
| diabetes_safety_net_gap | 1 | 5 | 35 | 4 | 0.114 | 0.020 | 1: 4 |
| documentation_photo_gap | 1 | 5 | 35 | 1 | 0.029 | 0.020 | 1: 1 |
| ectopic_pregnancy_escalation_gap | 1 | 5 | 35 | 2 | 0.057 | 0.020 | 1: 2 |
| medication_adherence_gap | 1 | 5 | 35 | 4 | 0.114 | 0.020 | 1: 4 |
| medication_dosing_risk | 5 | 25 | 175 | 16 | 0.091 | 0.020 | 1: 16 |
| medicolegal_followup_gap | 9 | 29 | 203 | 11 | 0.054 | 0.020 | 1: 11 |
| opioid_safety_net_gap | 1 | 5 | 35 | 4 | 0.114 | 0.020 | 1: 4 |
| over_inference_from_uncertain_transcript | 2 | 10 | 70 | 4 | 0.057 | 0.020 | 1: 4 |
| preventive_care_followup_gap | 1 | 5 | 35 | 3 | 0.086 | 0.020 | 1: 3 |
| renal_medication_interaction | 1 | 5 | 35 | 3 | 0.086 | 0.020 | 1: 3 |
| results_followup_ownership_gap | 1 | 5 | 35 | 3 | 0.086 | 0.020 | 1: 3 |
| skin_cancer_referral_gap | 1 | 5 | 35 | 1 | 0.029 | 0.020 | 1: 1 |
| suicide_risk_documentation_gap | 1 | 5 | 35 | 1 | 0.029 | 0.020 | 1: 1 |
| unsupported_hallucination | 11 | 39 | 273 | 14 | 0.051 | 0.020 | 1: 14 |
| withdrawal_risk_gap | 1 | 5 | 35 | 2 | 0.057 | 0.020 | 1: 2 |
| work_certificate_documentation_gap | 1 | 5 | 35 | 0 | 0.000 | 0.000 | none |
