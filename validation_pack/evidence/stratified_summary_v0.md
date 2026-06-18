# Stratified Validation Evidence Summary v0

This report links calibration pairs back to corpus metadata so agreement
coverage can be reviewed by specialty, note source, prompt strategy, and
safety-critical failure mode.

Illustrative synthetic reviewer ratings only. Replace with independent clinician ratings before making clinical validation claims.

## Coverage

- Cases: 20
- Submissions with evidence pairs: 100
- Evidence pairs: 118
- Dimensions: ahpra, hallucination, medication_terminology, medicolegal, omission, pdqi9, qnote

## Specialty

| Value | Cases | Submissions | Pairs | Dimensions | Mean abs diff | Severity exact agreement | Min weighted kappa | Min ICC(2,1) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| aged_care | 2 | 10 | 12 | 5 | 0.032 | 0.833 | 0.727 | 0.100 |
| chronic_disease | 2 | 10 | 12 | 5 | 0.033 | 1.000 | 1.000 | 0.000 |
| general_practice | 9 | 45 | 53 | 7 | 0.033 | 0.943 | 0.832 | 0.069 |
| mental_health | 1 | 5 | 6 | 5 | 0.032 | 1.000 | 1.000 | 0.981 |
| paediatrics | 2 | 10 | 12 | 6 | 0.029 | 0.917 | 0.800 | 0.000 |
| palliative_care | 1 | 5 | 5 | 5 | 0.034 | 1.000 | n/a | n/a |
| telehealth | 1 | 5 | 6 | 5 | 0.032 | 1.000 | 1.000 | 0.987 |
| urgent_care | 2 | 10 | 12 | 5 | 0.029 | 1.000 | 1.000 | 0.308 |

## Note Source

| Value | Cases | Submissions | Pairs | Dimensions | Mean abs diff | Severity exact agreement | Min weighted kappa | Min ICC(2,1) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| model_candidate | 20 | 80 | 98 | 7 | 0.033 | 0.990 | 0.952 | 0.160 |
| nurse_cdss | 20 | 20 | 20 | 5 | 0.025 | 0.750 | 0.000 | 0.112 |

## Prompt Strategy

| Value | Cases | Submissions | Pairs | Dimensions | Mean abs diff | Severity exact agreement | Min weighted kappa | Min ICC(2,1) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| cdss_checklist | 20 | 20 | 20 | 5 | 0.025 | 0.750 | 0.000 | 0.112 |
| cdss_informed | 20 | 20 | 21 | 3 | 0.029 | 1.000 | 1.000 | 0.134 |
| safety_first | 20 | 20 | 20 | 5 | 0.029 | 1.000 | 1.000 | 0.000 |
| standard | 20 | 20 | 37 | 5 | 0.036 | 1.000 | 1.000 | 0.733 |
| structured_soap | 20 | 20 | 20 | 4 | 0.036 | 0.950 | 0.833 | 0.200 |

## Failure Mode

| Value | Cases | Submissions | Pairs | Dimensions | Mean abs diff | Severity exact agreement | Min weighted kappa | Min ICC(2,1) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| anticoagulant_head_injury_escalation_gap | 1 | 5 | 6 | 4 | 0.028 | 0.833 | 0.750 | 0.978 |
| asthma_action_plan_gap | 1 | 5 | 6 | 5 | 0.030 | 1.000 | 1.000 | 0.992 |
| clinically_significant_omission | 18 | 90 | 107 | 7 | 0.032 | 0.944 | 0.867 | 0.182 |
| confidentiality_documentation_gap | 1 | 5 | 6 | 5 | 0.035 | 1.000 | 1.000 | 0.990 |
| contraception_contraindication_gap | 1 | 5 | 6 | 6 | 0.033 | 1.000 | n/a | n/a |
| copd_escalation_gap | 1 | 5 | 6 | 6 | 0.035 | 1.000 | n/a | n/a |
| culturally_safe_care_gap | 1 | 5 | 6 | 5 | 0.035 | 1.000 | 1.000 | 0.100 |
| delirium_escalation_gap | 1 | 5 | 6 | 5 | 0.035 | 0.833 | 1.000 | 0.995 |
| diabetes_safety_net_gap | 1 | 5 | 6 | 5 | 0.032 | 1.000 | 1.000 | 0.989 |
| documentation_photo_gap | 1 | 5 | 6 | 5 | 0.035 | 1.000 | 1.000 | 0.974 |
| ectopic_pregnancy_escalation_gap | 1 | 5 | 6 | 5 | 0.028 | 0.833 | 0.750 | 0.995 |
| medication_adherence_gap | 1 | 5 | 6 | 5 | 0.032 | 1.000 | 1.000 | 0.989 |
| medication_dosing_risk | 5 | 25 | 29 | 7 | 0.032 | 0.966 | 0.864 | 0.058 |
| medicolegal_followup_gap | 9 | 29 | 32 | 7 | 0.033 | 0.969 | 0.901 | 0.000 |
| opioid_safety_net_gap | 1 | 5 | 5 | 5 | 0.034 | 1.000 | n/a | n/a |
| over_inference_from_uncertain_transcript | 2 | 10 | 12 | 6 | 0.033 | 1.000 | 1.000 | 0.100 |
| preventive_care_followup_gap | 1 | 5 | 6 | 5 | 0.035 | 1.000 | 1.000 | 0.100 |
| renal_medication_interaction | 1 | 5 | 6 | 5 | 0.033 | 1.000 | 1.000 | 0.991 |
| results_followup_ownership_gap | 1 | 5 | 6 | 4 | 0.032 | 1.000 | 1.000 | 0.990 |
| skin_cancer_referral_gap | 1 | 5 | 6 | 5 | 0.035 | 1.000 | 1.000 | 0.974 |
| suicide_risk_documentation_gap | 1 | 5 | 6 | 5 | 0.032 | 1.000 | 1.000 | 0.981 |
| unsupported_hallucination | 11 | 39 | 50 | 7 | 0.032 | 0.920 | 0.859 | 0.053 |
| withdrawal_risk_gap | 1 | 5 | 6 | 5 | 0.035 | 1.000 | 1.000 | 0.990 |
| work_certificate_documentation_gap | 1 | 5 | 6 | 5 | 0.033 | 0.833 | 0.667 | 0.991 |
