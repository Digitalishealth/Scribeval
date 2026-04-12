# Scribeval Data Flow

This document describes exactly what data Scribeval sends where during evaluation. Clinical data governance is a first-class concern — every evaluation report includes a data flow disclosure section.

## What Data is Sent to the Anthropic API

When using the default LLM judge (Claude), the following data is sent to Anthropic's API for each evaluation dimension:

| Data | Sent? | Purpose |
|------|-------|---------|
| Consultation transcript (full text) | Yes | Compared against scribe output |
| AI scribe output note (full text) | Yes | The document being evaluated |
| Reference note (full text) | If provided | Used for comparison scoring |
| Evaluation rubric (YAML content) | Yes | Scoring criteria and instructions |
| Your Anthropic API key | Yes | Authentication only |

## What is NOT Sent

| Data | Sent? | Notes |
|------|-------|-------|
| Patient identifiers | Not by Scribeval | But may be present in your input files |
| File paths or system information | No | |
| Previous evaluation results | No | Each evaluation is independent |
| Your configuration settings | No | Only the model name is used in API calls |

## Optional: FHIR Terminology Server (medication_terminology dimension)

The `medication_terminology` dimension is **opt-in** and introduces a **second external service**: a FHIR R4 terminology server used to validate medication names against the Australian Medicines Terminology (AMT). It is not enabled by default.

### When this service is used

- Only when you explicitly request the `medication_terminology` dimension via `--dimensions medication_terminology`
- Default endpoint: `https://r4.ontoserver.csiro.au/fhir` (CSIRO public Ontoserver sandbox)
- Override with the `SCRIBEVAL_FHIR_TERMINOLOGY_URL` environment variable

### What is sent to the FHIR server

| Data | Sent? | Purpose |
|------|-------|---------|
| Extracted medication name strings | Yes | AMT lookup (e.g., `"amoxicillin"`) |
| Consultation transcript | **NO** | Never transmitted to FHIR endpoint |
| Full scribe note | **NO** | Never transmitted to FHIR endpoint |
| Patient identifiers | **NO** | Never transmitted to FHIR endpoint |
| Reference note | **NO** | Never transmitted to FHIR endpoint |

The two phases are deliberately separated so the FHIR server only ever sees short medication strings:

1. **Phase 1 (Anthropic API):** the LLM judge extracts medication mentions from the scribe note
2. **Phase 2 (FHIR server):** each extracted medication name is validated via `ValueSet/$expand` against AMT

Only the strings produced by Phase 1 are passed to Phase 2. Patient context, transcript content, and clinical narrative never reach the FHIR endpoint.

### Production guidance

- The default CSIRO public Ontoserver sandbox is **not appropriate for sensitive clinical data**
- For production use, **run your own Ontoserver** or use a contracted NCTS-licensed terminology service and set `SCRIBEVAL_FHIR_TERMINOLOGY_URL` accordingly
- Some Australian sites cannot send any clinical data outside their network — the entire dimension can be left disabled in those environments
- The terminology server's data handling policy is its operator's responsibility, not Scribeval's

### Graceful degradation

If the FHIR endpoint is unreachable or times out, the `medication_terminology` dimension returns a degraded score (0.0 with confidence 0.0) and a warning finding. **Other dimensions are unaffected.** Scribeval will not silently retry or escalate.

## Anthropic's Data Handling

- API inputs are **not used for model training** by default
- See Anthropic's data retention policy: https://www.anthropic.com/policies
- Anthropic may retain API logs for safety and abuse monitoring purposes
- Contact Anthropic for enterprise data processing agreements if required

## Local Data

Scribeval stores the following locally:

- **Evaluation reports** (JSON and/or Markdown) in the output directory you specify
- **No caching** of clinical data between runs
- **No telemetry** — Scribeval does not phone home or collect usage data

## Your Responsibilities

1. **De-identify clinical data** before running evaluations. Scribeval does not perform de-identification. Remove or replace:
   - Patient names and identifiers
   - Dates of birth
   - Medicare numbers
   - Address and contact details
   - Any other identifying information

2. **Ensure appropriate authority** to process the clinical data through an external API. This may require:
   - Patient consent
   - Organisational data governance approval
   - Ethics committee approval (if used for research)

3. **Comply with the Privacy Act 1988** (Cth) and relevant state/territory health records legislation (e.g., Health Records Act 2001 (Vic), Health Records and Information Privacy Act 2002 (NSW)).

4. **Review Anthropic's data retention policy** to ensure it meets your organisation's requirements.

## Alternative: Local Evaluation

To avoid sending clinical data to any external API, use the `ManualJudge` (human expert scoring mode, available in Phase 2). In this mode:
- All evaluation is performed locally
- No data is transmitted to any external service
- A human expert scores each dimension using the CLI questionnaire

## Data Flow Diagram

```
┌─────────────────────┐
│   Your Input Files   │
│  (De-identified!)    │
│                      │
│  - transcript.txt    │
│  - scribe_output.txt │
│  - reference.txt     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│     Scribeval CLI    │
│                      │
│  Loads rubrics       │
│  Builds prompts      │
│  Parses responses    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐     ┌─────────────────────┐
│   Anthropic API      │────▶│   Claude Model       │
│                      │◀────│                      │
│  Receives:           │     │  Returns:            │
│  - Transcript text   │     │  - JSON scores       │
│  - Scribe note text  │     │  - Findings          │
│  - Reference text    │     │  - Reasoning         │
│  - Rubric criteria   │     │                      │
└─────────────────────┘     └─────────────────────┘
           │
           ▼
┌─────────────────────┐
│   Local Output       │
│                      │
│  - report.json       │
│  - report.md         │
│  (Your machine only) │
└─────────────────────┘
```

### With `medication_terminology` enabled (opt-in)

```
┌─────────────────────┐
│   Anthropic API      │
│                      │
│  Phase 1: LLM        │
│  extracts medication │
│  names from note     │
└──────────┬──────────┘
           │ medication strings only
           ▼
┌─────────────────────┐
│   FHIR Terminology   │
│   Server (Ontoserver)│
│                      │
│  Receives:           │
│  - "amoxicillin"     │
│  - "paracetamol"     │
│                      │
│  Does NOT receive:   │
│  - Transcript        │
│  - Scribe note       │
│  - Patient context   │
└─────────────────────┘
```

## Questions?

If you have questions about Scribeval's data handling, please open an issue on the repository.
