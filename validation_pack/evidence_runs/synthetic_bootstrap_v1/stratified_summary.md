# Stratified Validation Evidence Summary v0

This report links calibration pairs back to corpus metadata so agreement
coverage can be reviewed by specialty, note source, prompt strategy, and
safety-critical failure mode.

Independent clinician validation claims require a ready clinician review readiness report and qualified reviewer provenance.

## Coverage

- Cases: 20
- Submissions with evidence pairs: 100
- Evidence pairs: 1400
- Dimensions: ahpra, hallucination, medicolegal, omission, overall, pdqi9, qnote

## Specialty

| Value | Cases | Submissions | Pairs | Dimensions | Mean abs diff | Severity exact agreement | Min weighted kappa | Min ICC(2,1) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| aged_care | 2 | 10 | 140 | 7 | 0.014 | 0.971 | 0.865 | 0.989 |
| chronic_disease | 2 | 10 | 140 | 7 | 0.014 | 0.950 | 0.918 | 0.989 |
| general_practice | 9 | 45 | 630 | 7 | 0.014 | 0.973 | 0.917 | 0.989 |
| mental_health | 1 | 5 | 70 | 7 | 0.014 | 0.986 | 0.921 | 0.990 |
| paediatrics | 2 | 10 | 140 | 7 | 0.014 | 0.943 | 0.884 | 0.989 |
| palliative_care | 1 | 5 | 70 | 7 | 0.014 | 0.943 | 0.884 | 0.990 |
| telehealth | 1 | 5 | 70 | 7 | 0.014 | 0.943 | 0.884 | 0.990 |
| urgent_care | 2 | 10 | 140 | 7 | 0.014 | 0.986 | 0.938 | 0.989 |

## Note Source

| Value | Cases | Submissions | Pairs | Dimensions | Mean abs diff | Severity exact agreement | Min weighted kappa | Min ICC(2,1) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| model_candidate | 20 | 80 | 1120 | 7 | 0.014 | 0.958 | 0.904 | 0.991 |
| nurse_cdss | 20 | 20 | 280 | 7 | 0.014 | 1.000 | 1.000 | 0.000 |

## Prompt Strategy

| Value | Cases | Submissions | Pairs | Dimensions | Mean abs diff | Severity exact agreement | Min weighted kappa | Min ICC(2,1) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| cdss_checklist | 20 | 20 | 280 | 7 | 0.014 | 1.000 | 1.000 | 0.000 |
| cdss_informed | 20 | 20 | 280 | 7 | 0.014 | 0.979 | 0.500 | 0.000 |
| safety_first | 20 | 20 | 280 | 7 | 0.014 | 0.929 | 0.706 | 0.000 |
| standard | 20 | 20 | 280 | 7 | 0.014 | 0.943 | 0.688 | 0.000 |
| structured_soap | 20 | 20 | 280 | 7 | 0.014 | 0.982 | 0.600 | 0.807 |

## Failure Mode

| Value | Cases | Submissions | Pairs | Dimensions | Mean abs diff | Severity exact agreement | Min weighted kappa | Min ICC(2,1) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| anticoagulant_head_injury_escalation_gap | 1 | 5 | 70 | 7 | 0.014 | 0.971 | 0.865 | 0.990 |
| asthma_action_plan_gap | 1 | 5 | 70 | 7 | 0.014 | 0.943 | 0.884 | 0.990 |
| clinically_significant_omission | 18 | 90 | 1260 | 7 | 0.014 | 0.969 | 0.917 | 0.989 |
| confidentiality_documentation_gap | 1 | 5 | 70 | 7 | 0.014 | 0.971 | 0.865 | 0.990 |
| contraception_contraindication_gap | 1 | 5 | 70 | 7 | 0.014 | 0.971 | 0.865 | 0.990 |
| copd_escalation_gap | 1 | 5 | 70 | 7 | 0.014 | 0.986 | 0.930 | 0.990 |
| culturally_safe_care_gap | 1 | 5 | 70 | 7 | 0.014 | 0.957 | 0.894 | 0.990 |
| delirium_escalation_gap | 1 | 5 | 70 | 7 | 0.014 | 0.971 | 0.865 | 0.989 |
| diabetes_safety_net_gap | 1 | 5 | 70 | 7 | 0.014 | 0.943 | 0.884 | 0.990 |
| documentation_photo_gap | 1 | 5 | 70 | 7 | 0.014 | 0.986 | 0.921 | 0.990 |
| ectopic_pregnancy_escalation_gap | 1 | 5 | 70 | 7 | 0.014 | 0.971 | 0.865 | 0.989 |
| medication_adherence_gap | 1 | 5 | 70 | 7 | 0.014 | 0.943 | 0.884 | 0.990 |
| medication_dosing_risk | 5 | 25 | 350 | 7 | 0.014 | 0.954 | 0.934 | 0.989 |
| medicolegal_followup_gap | 9 | 29 | 406 | 7 | 0.014 | 0.973 | 0.931 | 0.988 |
| opioid_safety_net_gap | 1 | 5 | 70 | 7 | 0.014 | 0.943 | 0.884 | 0.990 |
| over_inference_from_uncertain_transcript | 2 | 10 | 140 | 7 | 0.014 | 0.971 | 0.947 | 0.993 |
| preventive_care_followup_gap | 1 | 5 | 70 | 7 | 0.014 | 0.957 | 0.894 | 0.990 |
| renal_medication_interaction | 1 | 5 | 70 | 7 | 0.014 | 0.957 | 0.918 | 0.990 |
| results_followup_ownership_gap | 1 | 5 | 70 | 7 | 0.014 | 0.957 | 0.894 | 0.990 |
| skin_cancer_referral_gap | 1 | 5 | 70 | 7 | 0.014 | 0.986 | 0.921 | 0.990 |
| suicide_risk_documentation_gap | 1 | 5 | 70 | 7 | 0.014 | 0.986 | 0.921 | 0.990 |
| unsupported_hallucination | 11 | 39 | 546 | 7 | 0.014 | 0.974 | 0.917 | 0.992 |
| withdrawal_risk_gap | 1 | 5 | 70 | 7 | 0.014 | 0.971 | 0.865 | 0.990 |
| work_certificate_documentation_gap | 1 | 5 | 70 | 7 | 0.014 | 1.000 | 1.000 | 0.990 |
