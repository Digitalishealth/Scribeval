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

## Questions?

If you have questions about Scribeval's data handling, please open an issue on the repository.
