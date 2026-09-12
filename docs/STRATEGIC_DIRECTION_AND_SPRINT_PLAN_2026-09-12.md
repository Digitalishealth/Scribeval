---
title: Scribeval Strategic Direction and Sprint Plan
date: 2026-09-12
status: active
review_horizon: 90 days
---

# Scribeval — Strategic Direction and Sprint Plan

## Decision

**Invest and keep Scribeval independent of any one scribe product.** Its strongest strategic role is as an Australian transcript-to-note evaluation and assurance harness that can support product selection, internal QA and research. The next milestone is independent clinician validation and reproducible public methodology, not more evaluator dimensions.

Scribeval must remain explicit that it is a research/quality-assurance tool, not a validated clinical authority or medical device.

## Strategic priorities

1. Complete independent clinician review using the existing blinded workflow and pre-specified analysis plan.
2. Quantify inter-rater reliability and Scribeval-versus-clinician agreement before making performance claims.
3. Preserve product/vendor neutrality and blinded scoring.
4. Version judge model, prompt/rubric, corpus, source hash and run configuration for every report.
5. Separate synthetic/bootstrap evidence from independent validation evidence in all publication surfaces.
6. Make comparisons robust to model stochasticity, note style and specialty mix.
7. Use Scribeval as the acceptance harness for Scribbler and any future scribing product integrations.

## Sprint SV-01 — Independent Validation Execution

**Cadence:** 2 weeks  
**Objective:** run the first defensible independent clinician-validation cohort through the existing evidence pipeline and produce a claim-readiness decision.

| ID | Work item | Acceptance evidence |
|---|---|---|
| SV01-01 | Freeze validation protocol and analysis plan version | Hash/version recorded before review data; no outcome-driven protocol changes |
| SV01-02 | Recruit/qualify reviewer panel | Role/specialty/training eligibility met; identifiers kept outside public evidence |
| SV01-03 | Generate blinded reviewer assignments | Balanced case/stratum assignment; source/product labels hidden; assignment manifest hashed |
| SV01-04 | Complete reviewer training and calibration exercise | Training completion + pilot agreement threshold before production ratings |
| SV01-05 | Collect independent ratings | Two qualified reviewers per required case/dimension; completeness audit green |
| SV01-06 | Export frozen Scribeval judge scores | Exact code/model/rubric configuration and run hashes retained |
| SV01-07 | Calculate clinician inter-rater reliability | Weighted kappa/ICC and disagreement profile by dimension/stratum |
| SV01-08 | Build consensus and adjudication set | Disagreements flagged; adjudicator blinded; final consensus provenance retained |
| SV01-09 | Compare Scribeval with clinician consensus | Agreement, MAE, severity agreement, CIs and failure-mode analysis; no cherry-picked dimensions |
| SV01-10 | Stress-test robustness | Multi-run variance, ASR noise, specialty overlays, sensitivity to weights and judge provider/model |
| SV01-11 | Build validation evidence bundle | No raw PHI/reviewer identifiers; complete hashes, provenance, protocol and readiness status |
| SV01-12 | Publish claim-readiness decision | Explicit claims allowed/not allowed; limitations; minimum evidence before external marketing/procurement use |

### Exit gate

- protocol and analysis plan were frozen before outcome review;
- required independent reviewer coverage is complete;
- reviewer reliability is reported, not assumed;
- synthetic examples are not represented as validation;
- claims map directly to measured agreement and uncertainty;
- failed strata remain visible rather than averaged away.

## SV-02 — Benchmark release discipline

Create a versioned benchmark release with stable corpus schema, evaluator configuration, changelog, reproducibility command, expected variance and a blinded vendor-submission path. Add regression thresholds that prevent a release from silently reducing safety-critical detection.

## SV-03 — Product-selection workflow

Package the benchmark for a clinical governance/procurement audience: fixed comparison protocol, cost/latency reporting, safety-critical error summaries, uncertainty and decision caveats. Pilot it against Scribbler plus at least one external/synthetic comparator without changing scoring to favour any product.

## Measures

- independent reviewer coverage complete for the planned cohort;
- inter-rater reliability reported for every claim-bearing dimension;
- reproducible run from pinned corpus/config;
- zero product-specific scoring branches;
- every externally visible performance claim linked to a validation bundle and limitations statement.
