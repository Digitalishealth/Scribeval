# Changelog

All notable changes to Scribeval will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added — Critique-defence functionality

- **Reproducibility controls**: judge temperature pinned to 0 by default;
  input, rubric, and prompt content hashes embedded in every report via a
  new `ReproducibilityMetadata` block on `EvaluationReport`.
- **Multi-run variance**: `EvaluationPipeline(runs=N)` evaluates each
  dimension N times and reports per-run mean, standard deviation, and 95%
  confidence interval. Helps quantify judge instability.
- **Blinded transcript-to-note comparison** (`scribeval compare`): head-to-head
  comparison of multiple final notes on the same transcript with anonymised
  labels (`S1`, `S2`, ...), seeded randomised order, stripped submission names,
  and optional JSON/Markdown comparison reports for product-choice review.
- **Multi-case benchmark aggregation** (`scribeval benchmark`): manifest-driven
  product comparison across multiple transcripts with mean score, cross-case
  score standard deviation, critical-finding counts, and JSON/Markdown reports.
- **Error injection harness** (`scribeval.error_injection`): deterministic
  corruption taxonomy with 8 error types (missing allergy, fabricated
  finding, wrong drug/dose, missing red flag, fabricated medication,
  omitted management, wrong laterality). Provides ground-truth recall
  scoring for evaluator validation.
- **Calibration workflow** (`scribeval.calibration`): Cohen's weighted
  kappa (linear and quadratic) and ICC(2,1) absolute agreement,
  implemented from the primary literature in pure Python so that
  reviewers can audit the formulas without trusting a package.
- **Multi-judge ensemble** (`scribeval.judges.ensemble.EnsembleJudge`):
  wraps multiple judges, merges responses (mean score, worst severity,
  union findings), and penalises effective confidence when judges
  disagree.
- **Human-rater judge** (`scribeval.judges.human.HumanJudge`): interactive
  TTY questionnaire that implements `BaseJudge` so any evaluator can be
  driven by a clinician without code changes. Supports canned responses
  for tests.
- **Specialty-aware rubric overlays**: `RubricSchema.specialty_overlays`
  allows a rubric to define per-consultation-type weight multipliers,
  additional criteria, and severity escalation (e.g., hallucination
  weighted 1.3x in ED).
- **Sensitivity analysis** (`scribeval.sensitivity`): cheap post-hoc
  perturbation analysis on an existing `EvaluationReport` that reports
  whether the overall score is robust to plausible weight and severity
  variations.
- **ASR-noise simulator** (`scribeval.asr_noise`): seeded deterministic
  transcript corruption simulating homophone substitutions, hesitation
  fillers, partial words, `[inaudible]` markers, speaker swaps,
  crosstalk, and background noise. Lets users measure robustness of a
  scribe on noisy input without re-recording audio.
- **Cost and latency profiling** (`scribeval.profiling.ProfilingJudge`):
  judge-decorator that records per-call wall time and token-count
  estimates, producing an auditable per-dimension cost breakdown.
- **Expanded synthetic benchmark corpus**: added `case_paeds_fever` and
  `case_specialist_diabetes` sample cases with distinct planted-error
  categories (dose safety, hallucinated patient history, omitted
  referrals).

### Added — Publishing hygiene

- `LICENSE` file (MIT) with a prominent non-legal medical-device
  disclaimer.
- `CONTRIBUTING.md` with a clinician-friendly rubric-review path that
  does not require a development environment.
- `SECURITY.md` covering credential handling, outbound data flow, and
  privacy guidance.
- `CHANGELOG.md` (this file).
- `ROADMAP.md` listing deferred work and the status of each critique-
  defence tier.
- Prominent "NOT A MEDICAL DEVICE" notice embedded in every
  `EvaluationReport` via the `notice` field.
- Fail-closed FHIR: `fhir_terminology_url` must be explicitly configured
  when enabling `medication_terminology`; the opt-in dimension no longer
  silently uses a default public endpoint.
- GitHub Actions CI workflow running tests and lint on every push.

### Changed

- Scribeval is now framed as a transcript-to-note quality benchmark. CLI aliases
  `--candidate-note` and `--candidate-label` were added while preserving
  `--scribe-note` and `--scribe-product`.
- `LLMJudge` now accepts explicit `temperature`, `max_tokens`, and `seed`
  constructor parameters. Default temperature is 0.0.
- `EvaluationReport` now includes `reproducibility`, `run_statistics`,
  `specialty_weight_multipliers`, and a prominent `notice` disclaimer.
- `_compute_overall_score` accepts optional per-dimension specialty
  weight multipliers so a rubric overlay can boost a dimension's
  contribution.

## [0.1.0] — 2025-04-12

### Added

- Initial Scribeval release with 6 default dimensions (omission,
  hallucination, medicolegal, AHPRA, PDQI-9, QNOTE) and one opt-in
  dimension (medication_terminology).
- YAML rubric system with Pydantic validation.
- Click-based CLI with `evaluate`, `list-dimensions`, `validate-rubric`,
  and `show-data-flow` commands.
- JSON and markdown report formats.
- Synthetic sample cases (`case_gp_respiratory`, `case_ed_chest_pain`,
  `case_psych_review`).
- `DATA_FLOW.md` and `METHODOLOGY.md` documentation.
