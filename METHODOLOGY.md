# Scribeval Methodology

This document explains the design decisions behind Scribeval's evaluation framework, the literature basis for each scoring choice, and the trade-offs of dimensions that were considered but excluded.

## Design Principles

1. **Clinical safety dimensions are weighted higher than structural ones.** A note that captures all the right facts but is poorly formatted is safer than a polished note with a fabricated allergy.
2. **Severity-weighted scoring.** A single critical error pulls the overall score down more than several low-severity issues. Averaging treats a missed penicillin allergy the same as a slightly verbose history — that is wrong.
3. **Validated instruments alongside bespoke evaluators.** PDQI-9 and QNOTE were validated against clinician judgement in published research; they ground the score in instruments that pre-date AI scribes.
4. **Opt-in for anything that introduces external dependencies or privacy implications.** The default dimension set should run with one API (Anthropic) and no other network calls.
5. **Honest scoring.** If a service is unreachable, return a degraded score with confidence 0 — never paper over silently.

## Dimension Weights

| Dimension | Weight | Rationale |
|---|---|---|
| Hallucination | 2.0 | Fabricated information is the highest-risk failure mode (Kernberg et al. 2024). Hallucinations may go undetected because they read plausibly. |
| Omission | 1.5 | Clinically significant omissions can cause harm via missed allergies, red flags, or management steps (Tierney et al. 2024). Weighted lower than hallucination because clinicians often catch omissions during note review. |
| Medication Terminology (opt-in) | 1.5 | When enabled, this dimension validates the highest-harm error category — medication errors (Slight 2019, Westbrook 2010). |
| QNOTE | 1.2 | Domain-based instrument validated against clinical note utility (Burke et al. 2014). Two of the eight domains are safety-critical (medications/allergies, assessment/plan). |
| Medicolegal | 1.0 | Documentation deficiencies contribute to ~30% of successful malpractice claims in Australian general practice (Avant Mutual data). |
| AHPRA | 1.0 | Regulatory compliance. Important but less directly tied to immediate patient safety than clinical accuracy. |
| PDQI-9 | 1.0 | Validated holistic quality instrument (Stetson et al. 2012). Weighted at baseline because it overlaps with other dimensions. |

## Severity Penalty

In addition to dimension-weighted averaging, Scribeval applies a **severity penalty** based on individual findings:

| Severity | Per-finding weight |
|---|---|
| critical | 4.0 |
| high | 2.0 |
| moderate | 1.0 |
| low | 0.25 |
| none | 0.0 |

The total weighted finding contribution is normalised to a penalty in `[0.0, 0.60]` and applied as `adjusted = base_score * (1.0 - penalty)`. This is soft-capped at 0.60 so that one dimension cannot zero out the entire evaluation.

**Literature basis:**
- Slight et al. (2019) — medication errors account for disproportionate patient harm relative to their frequency.
- Westbrook et al. (2010) — severity of clinical errors follows a power-law distribution in harm outcomes.
- Reason J (2000) — Swiss cheese model: critical errors represent aligned failure points with outsized consequences.

## The Medication Terminology Decision

The `medication_terminology` dimension was the result of a deliberate scoping exercise. The original proposal was a broad terminology evaluator covering SNOMED CT-AU (conditions), AMT (medications), and LOINC (pathology). After review, this was scoped down to **AMT medication validation only** and made opt-in.

### What it does

1. **Phase 1 (LLM extraction):** the judge extracts medication mentions from the scribe note — drug name, strength, form, context.
2. **Phase 2 (FHIR validation):** each extracted medication is validated against the Australian Medicines Terminology (AMT) via a FHIR R4 terminology server (`ValueSet/$expand`).

Each medication produces a finding classified as:

| Outcome | Per-item score | Severity |
|---|---|---|
| `valid_exact` — single exact match | 1.0 | none |
| `valid_variant` — single match, variant naming | 0.9 | low |
| `valid_less_specific` — substring match, more specific concept exists | 0.6 | moderate |
| `ambiguous` — multiple matches, no exact | 0.3 | high |
| `invalid` — no match in AMT | 0.0 | critical |
| `lookup_failed` — server-side error | 0.0 | low |

If any medication is `invalid`, the dimension score is **capped at 0.5** regardless of how many other medications validate cleanly. A single fabricated drug is a safety event that cannot be averaged away.

### Why scoped to medications only

When concrete failure modes are mapped to validation capabilities, medications are the only category where AMT validation reliably catches errors that the LLM judge could plausibly miss:

| Error type | AMT catches | LLM judge catches |
|---|---|---|
| Misspelled drug name | Yes | Mostly |
| Fabricated drug name | Yes | Mostly |
| Wrong dose vs transcript | No | Yes |
| Wrong frequency | No | Yes |
| Brand vs generic | Maybe | Correctly handled |
| Drug omitted entirely | No | Yes (omission evaluator) |

The marginal value over the LLM judge for **conditions and procedures** is even smaller. Free-text descriptions like "acute viral upper respiratory tract infection" might not validate exactly against SNOMED CT-AU even though they are clinically correct, leading to a high false-positive rate. Restricting to medications keeps signal-to-noise high.

### Why opt-in rather than default

- Adds an external service dependency (network calls, latency, flakiness)
- Sends additional data to a second external service (privacy/governance complexity)
- Some Australian sites cannot send any data to a public Ontoserver sandbox; production users should run their own
- Default users get a fast, focused evaluation with one external dependency; specialists who care about medication coding opt in

### Limitations

- Validates **terminology only**, not clinical appropriateness. A medication may validate against AMT but still be wrong for the patient.
- Catches non-existent or imprecise drug names, not wrong-drug or wrong-dose errors.
- Does not validate doses, frequencies, or routes against any standard.
- The LLM extraction phase is an additional source of error — extraction failures are surfaced as graceful-degradation findings.

## Considered and Rejected: Broad Terminology Validation

We initially considered building a broad terminology evaluator covering SNOMED CT-AU conditions, AMT medications, and LOINC pathology. This was **rejected** in favour of the medication-only scope above.

### Reasoning

Today's AI scribes produce free-text clinical prose intended for human reading, not structured coded data for machine parsing. For free-text evaluation, terminology validation catches a narrow slice of errors (misspellings, non-existent terms) that the LLM judge — which has the consultation transcript as ground truth — already catches well.

The marginal evaluation improvement does not justify:
- A new external service dependency for every dimension
- Additional data flow to a second external service for every dimension
- The implementation, testing, and maintenance burden
- Dilution of focus from the core evaluation dimensions

### When this decision should be revisited

- When AI scribes begin producing structured FHIR resources with coded fields
- When evaluating a scribe that explicitly claims SNOMED CT-AU encoding as a feature
- When aggregate population-level terminology quality monitoring becomes a use case

### Note on Codeagogo

Codeagogo (`aehrc/codeagogo`) is a native macOS GUI utility for clinician code lookup, not a library. It has no Python API or CLI and cannot be imported. Even the underlying pattern (FHIR `$validate-code` against Ontoserver) is the wrong tool for free-text scribe evaluation today, for the reasons above.

## Validated Instruments

### PDQI-9 (Stetson et al. 2012)

The Physician Documentation Quality Instrument is a 9-item rating tool validated against clinician judgement of note quality. Items: up-to-date, accurate, thorough, useful, organised, comprehensible, succinct, synthesised, internally consistent. Each item is scored 1-5; Scribeval normalises to `(mean - 1) / 4`.

### QNOTE (Burke et al. 2014)

QNOTE assesses 8 clinical note domains: presenting complaint, history of presenting illness, past medical history, medications & allergies, review of systems, physical examination, assessment & plan, and overall impression. Two domains (medications/allergies, assessment/plan) are flagged safety-critical and receive elevated sub-weights. Domains marked N/A are excluded from the per-note score.

## References

- Burke HB, Hoang A, Becher D, et al. "QNOTE: an instrument for measuring the quality of EHR clinical notes." *JAMIA* 2014;21(5):910-916.
- Coiera E, et al. "The digital scribe." *npj Digital Medicine* 2018;1:58.
- Dean SM, et al. "Re-evaluation of PDQI-9 in the era of AI scribes." *JAMIA Open* 2023.
- Kernberg A, Gold JA, Mohan V. "Accuracy of AI-generated clinical documentation: a comparison study." *JAMIA* 2024.
- Reason J. "Human error: models and management." *BMJ* 2000;320:768-770.
- Roughead EE, Semple SJ. "Medication safety in Australia: a snapshot." *Australian Commission on Safety and Quality in Health Care*, 2013.
- Slight SP, et al. "The vital role of medication reconciliation in patient safety." *BMJ Quality & Safety* 2019;28(2):85-87.
- Stetson PD, Bakken S, Wrenn JO, Siegler EL. "Assessing electronic note quality using the Physician Documentation Quality Instrument (PDQI-9)." *Applied Clinical Informatics* 2012;3(2):164-174.
- Tierney AA, et al. "Ambient Artificial Intelligence Scribes to Alleviate the Burden of Clinical Documentation." *NEJM Catalyst* 2024.
- Van Buchem MM, et al. "The digital scribe in clinical practice." *npj Digital Medicine* 2021.
- Westbrook JI, et al. "Association of interruptions with an increased risk and severity of medication administration errors." *BMJ* 2010;340:c439.
- Australian Digital Health Agency. *Australian Medicines Terminology (AMT) Editorial Policy.*
- Medical Board of Australia. *Good Medical Practice: A Code of Conduct for Doctors in Australia.*
