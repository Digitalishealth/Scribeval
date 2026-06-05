# Roadmap

This document tracks deferred work and the status of the critique-defence
tiers that shape Scribeval's development.

## Phase 1 (shipped in 0.1.0)

- Core evaluation dimensions: omission, hallucination, medicolegal, AHPRA,
  PDQI-9, QNOTE
- YAML rubric system, Click CLI, JSON and markdown reporting
- Synthetic sample cases and data-flow disclosure
- Opt-in `medication_terminology` evaluator with FHIR/AMT validation
- Transcript-to-note candidate scoring, including optional GP-vs-AI comparison

## Phase 2 — critique-defence work (shipped in current release)

Tiered response to anticipated clinician and scribe-vendor critiques.

### Tier 1 — Reproducibility and validation (shipped)

- [x] Reproducibility controls: temperature=0, content hashing, seed
- [x] Multi-run variance reporting (`--runs N`)
- [x] Blinded head-to-head comparison with durable JSON/Markdown reports
      (`scribeval compare`)
- [x] Multi-case product benchmark aggregation (`scribeval benchmark`)
- [x] Error injection harness (`scribeval verify-detection`)
- [x] Calibration workflow with Cohen's κ / ICC (`scribeval calibrate`)

### Tier 2 — Model and clinician diversity (shipped)

- [x] Multi-judge ensemble (`EnsembleJudge`)
- [x] Human-rater judge (`HumanJudge`)
- [x] Specialty-aware rubric overlays
- [x] Sensitivity analysis (`scribeval sensitivity`)

### Tier 3 — Robustness and cost (shipped)

- [x] ASR-noise transcript simulator
- [x] Cost and latency profiling (`ProfilingJudge`)
- [x] Expanded synthetic benchmark corpus

## Phase 3 — deferred work

The items below are intentionally deferred. They are not shipped because
their cost exceeds their current value, or they require external
engagement (peer review, clinical partnerships) that is not a code
change.

### Peer review and external validation

- [x] Clinician-facing validation pilot pack with blinded worksheet and example
      calibration outputs
- [x] Bootstrap validation corpus and synthetic evidence trail with audit script
- [ ] Publication of the rubric framework for formal clinical review
- [ ] Multi-institution calibration study producing published κ / ICC
      against clinician raters
- [ ] Registration of the benchmark corpus with a synthetic-data DOI

### Corpus expansion

- [x] 20-case full transcript/note synthetic validation corpus across
      specialties
- [ ] 20+ full transcript/note runnable benchmark cases wired into
      `scribeval benchmark` (sample runnable corpus current: 5; validation
      corpus current: 20)
- [ ] Multi-speaker cases with recorded audio alignment
- [ ] Paediatric, palliative, remote/telehealth cases

### Adversarial robustness

- [ ] Prompt-injection resistance tests on scribe outputs
- [ ] Deliberately ambiguous transcripts to measure over-inference

### Deployment features

- [ ] Containerised run-it-yourself image
- [ ] Web UI for non-technical reviewers
- [ ] CSV / FHIR Bundle input formats
- [ ] Resumable batch mode for very large benchmark runs
- [ ] Configurable per-organisation dimension weights

### Additional evaluators (considered and rejected for now)

See `METHODOLOGY.md` for the full rationale. Briefly:

- Semantic accuracy, structural completeness, clinical reasoning fidelity,
  patient safety signals, privacy handling — overlap substantially with
  existing dimensions and would dilute focus
- Full SNOMED CT-AU condition validation — high false-positive rate against
  free-text clinical prose
- LOINC pathology validation — narrow scope for general scribe evaluation

## How to influence the roadmap

- Open an issue describing a concrete use-case and the evaluation gap
- Contribute a synthetic case or a rubric review
- Run a calibration study against your own clinicians and share the
  kappa/ICC results
