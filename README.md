# Scribeval

**An open evaluation framework for AI medical scribes in Australian healthcare.**

Scribeval provides a structured, evidence-based harness for scoring any AI medical scribe against clinical safety dimensions. It is grounded in Australian regulatory requirements (AHPRA, RACGP, Medicare/PBS) and current medical literature on clinical documentation quality.

## Why Scribeval?

AI medical scribes (Heidi Health, Lyrebird, Nabla, etc.) generate clinical notes from consultations, but there is no standardised, open benchmark to measure their safety and quality — particularly in the Australian context. Scribeval fills this gap.

## Evaluation Dimensions

| Dimension | What it measures |
|-----------|-----------------|
| **Omission** | Clinically significant information dropped from the note |
| **Hallucination** | Fabricated or incorrect clinical information added to the note |
| **Medicolegal Adequacy** | Whether documentation meets medicolegal protection standards |
| **AHPRA Compliance** | Alignment with Medical Board of Australia standards |

Additional dimensions (semantic accuracy, structural completeness, medication safety, clinical reasoning fidelity, patient safety signals, privacy handling) are planned for future releases.

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
