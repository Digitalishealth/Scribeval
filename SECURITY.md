# Security Policy

## Reporting a vulnerability

Please report security issues privately by emailing the maintainers rather
than opening a public issue. We will acknowledge receipt within a few working
days and aim to provide a fix or mitigation promptly for confirmed issues.

## Scope

Scribeval is an evaluation harness. Its primary security-relevant surfaces are:

1. **API credentials** — Scribeval reads `SCRIBEVAL_ANTHROPIC_API_KEY` from
   the environment. It does not persist the key and does not log it.
   Contributors must not commit secrets.
2. **Outbound data flow** — Scribeval sends consultation transcripts and
   scribe outputs to the configured LLM API (Anthropic by default) and, if
   the opt-in `medication_terminology` evaluator is enabled, extracted
   medication strings to the configured FHIR terminology server. See
   `DATA_FLOW.md` for details.
3. **Input file handling** — Scribeval reads local files specified on the
   CLI. It does not render or execute them. Do not pass untrusted files
   through the CLI.

## Privacy and clinical data

**Do not run Scribeval on identifiable patient data without ensuring your
organisation's governance allows the data to be sent to the external
services listed in `DATA_FLOW.md`.** De-identification is the caller's
responsibility.

For sensitive environments:
- Run your own Ontoserver instance and configure
  `SCRIBEVAL_FHIR_TERMINOLOGY_URL` to point at it.
- Use an enterprise Anthropic tenancy with a suitable data-handling
  agreement, or use the `HumanJudge` to score locally without any external
  API call.

## Not a medical device

Scribeval is **not** TGA-registered, **not** clinically validated, and
**not** intended for use as a medical device. It produces indicative
quality and safety signals that are suitable for research, procurement
assessment, and internal quality assurance — but not for primary clinical
decision-making.
