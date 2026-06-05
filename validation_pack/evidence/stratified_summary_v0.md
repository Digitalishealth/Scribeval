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

| Value | Cases | Submissions | Pairs | Dimensions | Mean abs diff | Severity exact agreement |
|---|---:|---:|---:|---:|---:|---:|
| aged_care | 2 | 10 | 12 | 5 | 0.032 | 0.833 |
| chronic_disease | 2 | 10 | 12 | 5 | 0.033 | 1.000 |
| general_practice | 9 | 45 | 53 | 7 | 0.033 | 0.943 |
| mental_health | 1 | 5 | 6 | 5 | 0.032 | 1.000 |
| paediatrics | 2 | 10 | 12 | 6 | 0.029 | 0.917 |
| palliative_care | 1 | 5 | 5 | 5 | 0.034 | 1.000 |
| telehealth | 1 | 5 | 6 | 5 | 0.032 | 1.000 |
| urgent_care | 2 | 10 | 12 | 5 | 0.029 | 1.000 |

## Note Source

| Value | Cases | Submissions | Pairs | Dimensions | Mean abs diff | Severity exact agreement |
|---|---:|---:|---:|---:|---:|---:|
| model_candidate | 20 | 80 | 98 | 7 | 0.033 | 0.990 |
| nurse_cdss | 20 | 20 | 20 | 5 | 0.025 | 0.750 |

## Prompt Strategy

| Value | Cases | Submissions | Pairs | Dimensions | Mean abs diff | Severity exact agreement |
|---|---:|---:|---:|---:|---:|---:|
| cdss_checklist | 20 | 20 | 20 | 5 | 0.025 | 0.750 |
| cdss_informed | 20 | 20 | 21 | 3 | 0.029 | 1.000 |
| safety_first | 20 | 20 | 20 | 5 | 0.029 | 1.000 |
| standard | 20 | 20 | 37 | 5 | 0.036 | 1.000 |
| structured_soap | 20 | 20 | 20 | 4 | 0.036 | 0.950 |

## Failure Mode

| Value | Cases | Submissions | Pairs | Dimensions | Mean abs diff | Severity exact agreement |
|---|---:|---:|---:|---:|---:|---:|
| anticoagulant_head_injury_escalation_gap | 1 | 5 | 6 | 4 | 0.028 | 0.833 |
| asthma_action_plan_gap | 1 | 5 | 6 | 5 | 0.030 | 1.000 |
| clinically_significant_omission | 18 | 90 | 107 | 7 | 0.032 | 0.944 |
| confidentiality_documentation_gap | 1 | 5 | 6 | 5 | 0.035 | 1.000 |
| contraception_contraindication_gap | 1 | 5 | 6 | 6 | 0.033 | 1.000 |
| copd_escalation_gap | 1 | 5 | 6 | 6 | 0.035 | 1.000 |
| culturally_safe_care_gap | 1 | 5 | 6 | 5 | 0.035 | 1.000 |
| delirium_escalation_gap | 1 | 5 | 6 | 5 | 0.035 | 0.833 |
| diabetes_safety_net_gap | 1 | 5 | 6 | 5 | 0.032 | 1.000 |
| documentation_photo_gap | 1 | 5 | 6 | 5 | 0.035 | 1.000 |
| ectopic_pregnancy_escalation_gap | 1 | 5 | 6 | 5 | 0.028 | 0.833 |
| medication_adherence_gap | 1 | 5 | 6 | 5 | 0.032 | 1.000 |
| medication_dosing_risk | 5 | 25 | 29 | 7 | 0.032 | 0.966 |
| medicolegal_followup_gap | 9 | 29 | 32 | 7 | 0.033 | 0.969 |
| opioid_safety_net_gap | 1 | 5 | 5 | 5 | 0.034 | 1.000 |
| over_inference_from_uncertain_transcript | 2 | 10 | 12 | 6 | 0.033 | 1.000 |
| preventive_care_followup_gap | 1 | 5 | 6 | 5 | 0.035 | 1.000 |
| renal_medication_interaction | 1 | 5 | 6 | 5 | 0.033 | 1.000 |
| results_followup_ownership_gap | 1 | 5 | 6 | 4 | 0.032 | 1.000 |
| skin_cancer_referral_gap | 1 | 5 | 6 | 5 | 0.035 | 1.000 |
| suicide_risk_documentation_gap | 1 | 5 | 6 | 5 | 0.032 | 1.000 |
| unsupported_hallucination | 11 | 39 | 50 | 7 | 0.032 | 0.920 |
| withdrawal_risk_gap | 1 | 5 | 6 | 5 | 0.035 | 1.000 |
| work_certificate_documentation_gap | 1 | 5 | 6 | 5 | 0.033 | 0.833 |
