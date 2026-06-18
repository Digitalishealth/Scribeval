# Scribeval

**An open transcript-to-note quality benchmark for Australian healthcare.**

> ⚠️ **NOT A MEDICAL DEVICE.** Scribeval is a research and quality-assurance
> tool. It is **not** TGA-registered, **not** clinically validated, and must
> **not** be used as the sole basis for clinical, procurement, or regulatory
> decisions. Results are indicative quality and safety signals only.
> See [`LICENSE`](LICENSE), [`SECURITY.md`](SECURITY.md), and
> [`METHODOLOGY.md`](METHODOLOGY.md) for the full disclaimer and limitations.

Scribeval provides a structured, evidence-based harness for scoring any final
clinical note against the whole consultation transcript. It can evaluate AI
scribe outputs and optionally compare them with a GP's ordinary non-AI note
using the same scoring path. It is grounded in Australian regulatory
requirements (AHPRA, RACGP, Medicare/PBS) and current medical literature on
clinical documentation quality.

## Why Scribeval?

AI medical scribes generate clinical notes from consultations, but there is no
standardised, open benchmark to measure the quality of the final note against
the whole transcript — particularly in the Australian context. Scribeval fills
this gap. It is product-agnostic: any scribe output can be submitted as a
candidate note.

Its benchmark role is analogous to public tools such as the SNOMED CT Entity
Linking Benchmark, but the target is different: Scribeval scores
transcript-to-note documentation quality, not SNOMED CT entity linking.

## Evaluation Dimensions

### Default dimensions (always run)

| Dimension | What it measures |
|-----------|-----------------|
| **Omission** | Clinically significant information dropped from the note |
| **Hallucination** | Fabricated or incorrect clinical information added to the note |
| **Medicolegal Adequacy** | Whether documentation meets medicolegal protection standards |
| **AHPRA Compliance** | Alignment with Medical Board of Australia standards |
| **PDQI-9** | 9-item validated note quality instrument (Stetson et al. 2012) |
| **QNOTE** | 8-domain clinical note quality instrument (Burke et al. 2014) |

### Opt-in dimensions

| Dimension | What it measures | Why opt-in |
|-----------|-----------------|------------|
| **Medication Terminology** | Validates medication names against the Australian Medicines Terminology (AMT) via a configurable FHIR R4 server | Adds a second external service (FHIR endpoint), only relevant for Australian medication coding, narrow safety-net scope |

To enable an opt-in dimension, request it explicitly:

```bash
scribeval evaluate \
    --dimensions omission,hallucination,medication_terminology \
    ...
```

See [METHODOLOGY.md](METHODOLOGY.md) for the design rationale, including dimensions that were considered and rejected.

## How It Works

1. **Provide inputs**: a consultation transcript and a candidate final note
   (a reference note is optional adjudication context, not a scored comparator)
2. **Scribeval evaluates** each dimension using clinically-informed rubrics and an LLM-as-judge approach (Claude)
3. **Receive a structured report** with per-dimension scores (0-1, where 1 = perfect), severity ratings, specific findings with evidence, and an overall score

Rubrics are defined in YAML and can be reviewed or customised by clinicians without touching code.

For optional comparison, pass multiple final notes for the same transcript. A
GP's non-AI note is treated as a comparable submission and receives its own
score.

## Data Transparency

Scribeval is explicit about data handling. Every evaluation report includes a **data flow disclosure** stating exactly what data was sent to which API. See [DATA_FLOW.md](DATA_FLOW.md) for full details.

**Important**: You are responsible for de-identifying clinical data before evaluation. Scribeval does not perform de-identification.

## Installation

```bash
pip install -e ".[dev]"
```

Requires Python 3.11+ and an Anthropic API key:

```bash
export SCRIBEVAL_ANTHROPIC_API_KEY=sk-ant-...
```

## Quick Start

```bash
# List available evaluation dimensions
scribeval list-dimensions

# Evaluate a scribe's output
scribeval evaluate \
    --transcript consultation.txt \
    --candidate-note final_note.txt \
    --consultation-type gp_standard \
    --candidate-label ScribeA

# Backward-compatible aliases still work:
#   --scribe-note is an alias for --candidate-note
#   --scribe-product is an alias for --candidate-label

# Optional GP-vs-AI comparison against the same transcript
scribeval compare \
    --transcript consultation.txt \
    --candidate-note GP=gp_note.txt \
    --candidate-note ScribeA=scribe_a_note.txt \
    --candidate-note ScribeB=scribe_b_note.txt \
    --candidate-note ScribeC=scribe_c_note.txt \
    --candidate-note ScribeD=scribe_d_note.txt \
    --runs 3 \
    --output comparison_report \
    --format both

# Multi-case benchmark for product selection
scribeval benchmark samples/benchmark_manifest.json \
    --dimensions omission,hallucination \
    --runs 3 \
    --output product_quality_benchmark \
    --format both

# Full 20-case validation corpus benchmark
scribeval benchmark validation_pack/corpus/benchmark_manifest.json \
    --dimensions omission,hallucination,medicolegal,ahpra,pdqi9,qnote \
    --output validation_corpus_benchmark \
    --format both

# Validate a rubric file
scribeval validate-rubric rubrics/omission.yaml

# See what data would be sent where
scribeval show-data-flow
```

## Critique-defence capabilities

Scribeval ships with a suite of features designed to answer the critiques
a serious clinician or scribe vendor will raise:

| Capability | Critique it answers |
|-----------|---------------------|
| `--runs N` multi-run variance with 95% CI | "LLM judges are stochastic, you got lucky" |
| Content hashing and temperature=0 by default | "This isn't reproducible" |
| `scribeval compare` (blinded head-to-head) | "You favoured your vendor" |
| `scribeval verify-detection` (error injection) | "How do we know the evaluator actually finds errors?" |
| `scribeval calibrate` (Cohen's κ, ICC(2,1)) | "How does this agree with clinicians?" |
| `EnsembleJudge` (multi-model) | "A single LLM is biased" |
| `HumanJudge` (TTY) | "Run it fully offline with real clinicians" |
| Specialty rubric overlays | "ED isn't the same as GP" |
| `scribeval sensitivity` | "The weights are arbitrary" |
| ASR-noise simulator | "Your transcripts are too clean" |
| `ProfilingJudge` cost and latency reporting | "We can't afford to run this regularly" |

See [`ROADMAP.md`](ROADMAP.md) for deferred items, and
[`CHANGELOG.md`](CHANGELOG.md) for the full list of capabilities in this
release.

For repository-publication status and the release smoke test, see
[`PUBLIC_RELEASE.md`](PUBLIC_RELEASE.md).

## Clinician Validation Pack

The [`validation_pack/`](validation_pack/) directory contains a clinician-facing
pilot protocol for testing Scribeval against independent human reviewers. It
includes a 20-case synthetic review manifest, a blinded reviewer worksheet, a
20-case synthetic corpus of complete transcript/note packets, generated blinded
reviewer packets, a clinician reviewer scoring guide, a pseudonymous reviewer
registry template, a reviewer intake checklist for public/private evidence
boundaries, a reviewer recruitment plan, a private reviewer attestation
template, a reviewer training guide, an independent-review runbook with private
workspace guardrails, a collection plan for planned stratum coverage, a
pre-specified statistical analysis plan, and example calibration inputs/results
for:

```bash
python scripts/build_reviewer_packets.py
python scripts/plan_reviewer_recruitment.py \
    --output-json validation_pack/reviewer_recruitment_plan.json \
    --output-md validation_pack/reviewer_recruitment_plan.md \
    --fail-on-incomplete
python scripts/plan_validation_collection.py \
    --output-json validation_pack/collection_plan.json \
    --output-md validation_pack/collection_plan.md \
    --fail-on-underpowered
python scripts/summarize_validation_goal_status.py \
    --output-json validation_pack/validation_goal_status.json \
    --output-md validation_pack/validation_goal_status.md
python scripts/import_validation_ratings.py \
    --worksheet validation_pack/evidence/synthetic_reviewer_worksheet_v0.csv \
    --judge-scores validation_pack/evidence/synthetic_scribeval_scores_v0.json \
    --output validation_pack/evidence/calibration_pairs_v0.json
python scripts/export_validation_judge_scores.py \
    --output <scribeval_scores.json> \
    --dimensions omission,hallucination,medicolegal,ahpra,pdqi9,qnote
python scripts/summarize_validation_review_run.py \
    --reviewer-registry <reviewer_registry.csv> \
    --assignments-dir <reviewer_assignments_dir> \
    --worksheet <filled_worksheet.csv> \
    --judge-scores <scribeval_scores.json> \
    --output-json <review_run_status.json> \
    --output-md <review_run_status.md> \
    --fail-on-not-ready
python scripts/summarize_reviewer_reliability.py \
    --worksheet <filled_worksheet.csv> \
    --reviewer-registry <reviewer_registry.csv> \
    --output-json <reviewer_reliability.json> \
    --output-md <reviewer_reliability.md> \
    --fail-on-not-ready
python scripts/build_consensus_validation_ratings.py \
    --worksheet <filled_worksheet.csv> \
    --reviewer-registry <reviewer_registry.csv> \
    --judge-scores <scribeval_scores.json> \
    --output <consensus_calibration_pairs.json> \
    --output-summary-json <consensus_summary.json> \
    --output-summary-md <consensus_summary.md>
python scripts/build_adjudication_packets.py \
    --consensus-pairs <consensus_calibration_pairs.json> \
    --output-dir <adjudication_packets_dir>
python scripts/import_adjudication_decisions.py \
    --consensus-pairs <consensus_calibration_pairs.json> \
    --adjudication-worksheet <filled_adjudication_worksheet.csv> \
    --reviewer-registry <reviewer_registry.csv> \
    --adjudicator-id <adjudicator_reviewer_id> \
    --require-qualified-adjudicator \
    --output <adjudicated_consensus_calibration_pairs.json> \
    --output-summary-json <adjudicated_consensus_summary.json> \
    --output-summary-md <adjudicated_consensus_summary.md>
python scripts/build_validation_evidence_bundle.py \
    --run-id <review_run_id> \
    --worksheet <filled_worksheet.csv> \
    --reviewer-registry <reviewer_registry.csv> \
    --judge-scores <scribeval_scores.json> \
    --reviewer-assignments-dir <reviewer_assignments_dir> \
    --adjudicated-consensus-pairs <adjudicated_consensus_calibration_pairs.json> \
    --output-dir validation_pack/evidence_runs
python scripts/assess_validation_claim_readiness.py \
    --evidence-manifest <evidence_manifest.json> \
    --output-json <validation_claim_readiness.json> \
    --output-md <validation_claim_readiness.md> \
    --fail-on-not-ready
python scripts/summarize_validation_evidence.py
scribeval calibrate validation_pack/results/example_calibration_pairs.json
scribeval calibrate validation_pack/evidence/calibration_pairs_v0.json
python scripts/validation_pack_audit.py
python scripts/audit_validation_evidence_runs.py
python scripts/build_synthetic_evidence_bundle.py
python scripts/index_validation_evidence_runs.py \
    --evidence-runs validation_pack/evidence_runs \
    --output-json validation_pack/evidence_runs/index.json \
    --output-md validation_pack/evidence_runs/index.md
```

The pack is intended to produce evidence about agreement with clinicians
(weighted kappa for severity ratings and ICC(2,1) for continuous scores). The
included example data is synthetic and illustrative only; it is not clinical
validation evidence. For independent clinician ratings, follow
`validation_pack/independent_review_runbook.json`, run
`scripts/build_reviewer_assignments.py` to create reviewer-specific worksheets
under an ignored private workspace, complete the coordinator-side
`validation_pack/reviewer_intake_checklist.json` and
`validation_pack/reviewer_attestation_template.json`, check
`validation_pack/reviewer_recruitment_plan.json` for reviewer panel targets,
check
`validation_pack/collection_plan.json` for planned coverage across
specialty, note source, prompt strategy, and safety-critical failure mode,
preserve `validation_pack/statistical_analysis_plan.json` as the pre-specified
interpretation contract,
check `validation_pack/validation_goal_status.json` for the current
claim-readiness boundary,
use `validation_pack/reviewer_training_guide.json` before setting
`training_completed=yes`,
run `scripts/audit_clinician_review_readiness.py`, export Scribeval scores with
`scripts/export_validation_judge_scores.py`, check clinician inter-rater
agreement with `scripts/summarize_reviewer_reliability.py`, build consensus
clinician ratings with `scripts/build_consensus_validation_ratings.py`, then run
`scripts/import_validation_ratings.py` with `--reviewer-registry` and
`--require-qualified-reviewers` so the calibration pairs carry reviewer
eligibility provenance without exposing direct identifiers. The generated
stratified summary shows whether agreement evidence spans specialties, note
sources, prompting strategies, and safety-critical failure modes, including
stratum-level weighted kappa, ICC(2,1), mean absolute difference, and severity
agreement where enough pairs exist. The readiness audit checks that every
blinded case-submission has two qualified reviewers and complete overall
note-quality and required dimension ratings before calibration import.
`scripts/summarize_validation_review_run.py` publishes an aggregate coordinator
status report across assignments, worksheet completion, reviewer provenance, and
judge-score availability without exposing reviewer identifiers, comments,
transcripts, notes, raw judge responses, or reasoning. The reviewer reliability
report shows whether clinician reviewers agree enough for their ratings to be a
defensible comparator. The consensus ratings provide a cleaner
judge-vs-clinician comparison and flag rows needing adjudication before strong
claims. `scripts/build_adjudication_packets.py` turns those flagged rows into
blinded adjudicator packets and a worksheet without reviewer IDs or candidate
source metadata. `scripts/import_adjudication_decisions.py` applies a qualified
adjudicator's decisions back to the consensus evidence and clears resolved
adjudication flags. The validation-claim readiness report applies explicit
protocol thresholds before treating the bundle as evidence for validation
claims. For a completed review run, `scripts/build_validation_evidence_bundle.py`
orchestrates these steps into one versioned bundle with the aggregate review-run
status, blinded reviewer-material hashes including the reviewer scoring guide,
source hashes, adjudication-burden summary, the reviewer assignment manifest
hash when supplied, and the adjudicated consensus-pair source hash when supplied.
`scripts/audit_validation_evidence_runs.py` checks generated bundles before
publication and rejects raw clinician CSV inputs. Use
`scripts/index_validation_evidence_runs.py` to publish a compact run index with
coverage, claim-readiness status, failed readiness checks, and agreement minima
across evidence bundles.
The committed `validation_pack/evidence_runs/synthetic_bootstrap_v1/` bundle is
generated by `scripts/build_synthetic_evidence_bundle.py` and is an illustrative
workflow artifact only, not independent clinical validation.

## Choosing a Scribe Product

For product selection, run each candidate note against the same de-identified
transcript and save the comparison report. Scribeval supports 2 to 5 candidate
notes per comparison, including an optional GP-written baseline:

```bash
scribeval compare \
    --transcript consultation.txt \
    --candidate-note GP=gp_note.txt \
    --candidate-note ScribeA=scribe_a_note.txt \
    --candidate-note ScribeB=scribe_b_note.txt \
    --candidate-note ScribeC=scribe_c_note.txt \
    --candidate-note ScribeD=scribe_d_note.txt \
    --runs 3 \
    --output product_quality_comparison \
    --format both
```

The terminal shows a simple ranked score table. The JSON and Markdown reports
preserve the unblinded ranking, per-dimension scores, severity summaries, and
findings so a clinical governance or procurement team can review the evidence.
Submissions are blinded while being scored; labels are revealed only in the
final report. Use `--runs 3` or higher for higher-stakes comparisons so the
report captures judge variance rather than a single point estimate.

For a more objective product-choice exercise, use the multi-case benchmark
command. The manifest requires every case to include the same 2 to 5 submission
labels:

```json
{
  "cases": [
    {
      "case_id": "case_001",
      "consultation_type": "gp_standard",
      "transcript": "case_001/transcript.txt",
      "candidate_notes": {
        "GP": "case_001/gp_note.txt",
        "ScribeA": "case_001/scribe_a_note.txt",
        "ScribeB": "case_001/scribe_b_note.txt",
        "ScribeC": "case_001/scribe_c_note.txt",
        "ScribeD": "case_001/scribe_d_note.txt"
      }
    }
  ]
}
```

`scribeval benchmark` ranks products by mean score across cases, reports
cross-case score standard deviation, counts critical findings, and preserves
case-level results for audit.

The 20-case validation corpus can also be run directly without generating
separate text files:

```bash
scribeval benchmark validation_pack/corpus/benchmark_manifest.json \
    --dimensions omission,hallucination,medicolegal,ahpra,pdqi9,qnote \
    --output validation_corpus_benchmark \
    --format both
```

## Demo Frontend

A static dashboard in [`frontend/`](frontend/) shows synthetic benchmark outputs
for Nurse + CDSS versus four product-agnostic model candidates, including
variation across prompting strategies and an example clinician calibration
view.

Live demo: <https://digitalishealth.github.io/Scribeval/>

```bash
python3 -m http.server 8765
```

Open `http://localhost:8765/frontend/`.

## Sample Cases

The `samples/` directory contains synthetic (entirely fictional) consultation cases with deliberately planted errors for demonstration and testing. **No real patient data is included.**

## Methodology

Scribeval uses an **LLM-as-judge** approach where each evaluation dimension has:

- A **YAML rubric** defining severity criteria, scoring guidelines, and Australian-specific context
- An **evaluator** that constructs a dimension-specific prompt with the rubric, inputs, and required output schema
- A **judge** (Claude by default, or a human expert) that scores the candidate
  final note against the rubric

Scores are normalised 0-1 across all dimensions (1 = perfect) for consistent comparison.

### Literature References

- Coiera E, et al. "The digital scribe." *npj Digital Medicine* (2018)
- Tierney AA, et al. "Ambient Artificial Intelligence Scribes to Alleviate the Burden of Clinical Documentation." *NEJM Catalyst* (2024)
- Van Buchem MM, et al. "The digital scribe in clinical practice." *npj Digital Medicine* (2021)
- Kernberg A, et al. "Accuracy of AI-generated clinical documentation." *JAMIA* (2024)
- RACGP Standards for General Practice, 5th Ed — Clinical Records
- Medical Board of Australia. "Good medical practice: a code of conduct for doctors in Australia"
- Avant Mutual. "Medical records — your obligations"
- MDA National. "Clinical documentation — a medicolegal guide"

## License

MIT
