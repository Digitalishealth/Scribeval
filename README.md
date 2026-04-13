# Scribeval

**An open evaluation framework for AI medical scribes in Australian healthcare.**

> ⚠️ **NOT A MEDICAL DEVICE.** Scribeval is a research and quality-assurance
> tool. It is **not** TGA-registered, **not** clinically validated, and must
> **not** be used as the sole basis for clinical, procurement, or regulatory
> decisions. Results are indicative quality and safety signals only.
> See [`LICENSE`](LICENSE), [`SECURITY.md`](SECURITY.md), and
> [`METHODOLOGY.md`](METHODOLOGY.md) for the full disclaimer and limitations.

Scribeval provides a structured, evidence-based harness for scoring any AI medical scribe against clinical safety dimensions. It is grounded in Australian regulatory requirements (AHPRA, RACGP, Medicare/PBS) and current medical literature on clinical documentation quality.

## Why Scribeval?

AI medical scribes (Heidi Health, Lyrebird, Nabla, etc.) generate clinical notes from consultations, but there is no standardised, open benchmark to measure their safety and quality — particularly in the Australian context. Scribeval fills this gap.

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

1. **Provide inputs**: a consultation transcript and the AI scribe's output note (a reference "gold standard" note is optional)
2. **Scribeval evaluates** each dimension using clinically-informed rubrics and an LLM-as-judge approach (Claude)
3. **Receive a structured report** with per-dimension scores (0-1, where 1 = perfect), severity ratings, specific findings with evidence, and an overall score

Rubrics are defined in YAML and can be reviewed or customised by clinicians without touching code.

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
    --scribe-note scribe_output.txt \
    --consultation-type gp_standard \
    --scribe-product heidi

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

## Sample Cases

The `samples/` directory contains synthetic (entirely fictional) consultation cases with deliberately planted errors for demonstration and testing. **No real patient data is included.**

## Methodology

Scribeval uses an **LLM-as-judge** approach where each evaluation dimension has:

- A **YAML rubric** defining severity criteria, scoring guidelines, and Australian-specific context
- An **evaluator** that constructs a dimension-specific prompt with the rubric, inputs, and required output schema
- A **judge** (Claude by default, or a human expert) that scores the scribe output against the rubric

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
