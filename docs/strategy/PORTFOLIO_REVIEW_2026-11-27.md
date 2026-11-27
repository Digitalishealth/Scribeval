# Scribeval — product strategy, roadmap and sprint baseline

**Review date:** 27 November 2026. **Verdict:** prioritise independent clinician validation and a bounded buyer-learning exercise; preserve vendor-neutral evaluation and avoid adding scoring breadth before external evidence.

## Strategic role

Scribeval's useful job is to make transcript-to-note comparisons reproducible, inspectable and appropriately uncertain for clinical governance, procurement and research. The intended users are evaluators and governance teams; the possible economic buyer is a health service or sponsor commissioning a fixed-scope comparative evaluation. A paid evaluation service is a hypothesis to test, not an established business or a claim of certification.

Do not position benchmark scores as clinical approval, regulatory approval or universal model rankings. Keep the evaluated unit as the whole transcript against the final note, with reference notes only optional adjudication context. Vendor identity, judge configuration, rubric/corpus versions, input hashes, run counts and uncertainty must remain traceable. Scoring must not favour any related product.

## What is actually ready

Default head is `5b58cb7691022072b0f30990d225ce68ae43fa57`. The repository contains scoring, CLI, rubric, reproducibility and clinician-review workflows. `validation_pack/validation_goal_status.json` explicitly reports **prepared_for_independent_clinician_review_not_validated** and `is_ready_for_validation_claim: false`.

The committed corpus has 20 synthetic cases and one synthetic bootstrap evidence run. Its 100 submissions, 1,400 individual calibration pairs and 700 consensus pairs demonstrate pipeline shape, not 100 clinically observed notes or independent reviewer work. The synthetic bundle records 47 adjudication-required items. Its apparently high agreement values must not appear as evidence of real clinician agreement. No claim-ready independent evidence run, paying customer or signed evaluation partner was established in the inspected records.

[PR #1](https://github.com/Digitalishealth/Scribeval/pull/1) has proposed independent validation since September and remains open. The bottleneck is reviewer/collection execution and independence, not another evaluator implementation.

## External signal and inference

[TGA's digital-scribe review, published 16 October 2026](https://www.tga.gov.au/resources/publication/corporate-reports/digital-scribe-review-outcomes), identified approximately 100 suppliers, focused on 12 products and considered eight likely to include medical-device functions. TGA did not test safety/performance or privacy. This supports investigating demand for careful evaluation and claims discipline; it does not establish that buyers will pay for Scribeval or that its current rubric is validated.

## 30/60/90-day roadmap

| Horizon | Outcome | Gate |
| --- | --- | --- |
| 30 days | Frozen independent-review package and qualified reviewer commitments | Protocol/version/hash, private eligibility/consent/conflict/training records, blinded assignments and collection responsibilities. Recruitment/outreach and paid/live evaluations require their own authority. |
| 60 days, reviewer-dependent | Completed first independent evidence run or explicit incomplete status | Required coverage, independent ratings, reviewer reliability, adjudication and judge-versus-consensus agreement with uncertainty; failed strata remain visible. |
| 90 days | Restricted claim decision and one reproducible evaluation offer | Claims map to evidence and limitations; buyer/user feedback on report utility and willingness to commission a scoped comparison; no assumed revenue. |

## Three sequential two-week work blocks

| Sprint | Work and owner roles | Acceptance evidence |
| --- | --- | --- |
| SV-R1 — organise independent collection | Evaluation lead + independent clinicians: freeze protocol/analysis; confirm reviewer/adjudicator roles and conflicts; prepare private blinded assignments | At least the existing minimum qualified panel and two ratings per required case/submission are planned; signed/private provenance outside this public repository; no tuning after outcomes are viewed. |
| SV-R2 — collect and adjudicate | Independent reviewers + coordinator: complete scoring; run completeness/reliability checks; resolve disputed ratings | Actual independent statuses, missingness and all disagreements recorded; no synthetic rows relabelled as human evidence; no outcome-driven rubric changes masquerading as pre-specification. Extend collection if incomplete. |
| SV-R3 — report and test utility | Evaluation lead + governance reviewer: frozen judge comparison, sensitivity/stochasticity analysis and aggregate report; separate buyer discovery | Pinned configurations and reproducible commands; confidence intervals appropriate to case-level dependence; failures and limitations stated; only non-identifying aggregate evidence public. Live model use/spend only if authorised. |

These are workload packages, not a promise that independent clinicians or buyers are available on the calendar. The analysis plan's planned pair count is not an independent sample size: repeated dimensions/submissions from the same case are clustered. Revisit power/precision claims with statistical review rather than treating 1,400 rows as 1,400 independent patients.

## Measures and stop rules

Measure genuine reviewer completion and coverage, per-dimension reliability, adjudication burden, agreement/sensitivity with uncertainty, reproducibility and reviewer effort. Hold validation claims where required coverage, reliability or adjudication is incomplete. Freeze feature expansion if the panel or buyer cannot be secured; a prepared benchmark is still useful research infrastructure. Do not publish raw clinical transcripts, private reviewer identities or vendor-submission secrets. Do not imply that one 20-case synthetic corpus supports real-world outcome claims.

This rebaseline supersedes the sequencing in `ROADMAP.md` and the stale draft PR #1 where they conflict. Methodology, security/publication controls and the existing claim boundary remain unchanged. No live evaluation, clinician recruitment or code test was run during this strategy review.
