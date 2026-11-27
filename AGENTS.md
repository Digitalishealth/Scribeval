# Scribeval agent guide

This is the maintained policy for the Australian transcript-to-note research/QA benchmark. Read `METHODOLOGY.md`, `DATA_FLOW.md`, `SECURITY.md` and `PUBLIC_RELEASE.md` before changing evaluation or publication behaviour.

## Map and commands

`src/scribeval` contains the Python CLI/evaluation pipeline; `rubrics` holds YAML scoring definitions; `tests` covers evaluations; `samples` and `validation_pack` contain synthetic and reviewer evidence workflows; `scripts` contains audits; `frontend` is the separate presentation surface.

Python >=3.11 is declared in `pyproject.toml`. With an already prepared development environment, use `pytest -q -m 'not live'`, `ruff check src/ tests/ scripts/`, `python scripts/public_release_audit.py`, `python scripts/validation_pack_audit.py` and `python scripts/audit_validation_evidence_runs.py` as relevant. CLI examples and rubric validation are in `README.md`; `scribeval` is the declared entry point.

## Evaluation invariants

Preserve rubric/version, model/provider/configuration, input hashes, run counts, scoring semantics, uncertainty and data-flow provenance so runs are reproducible and comparable. Candidate notes are scored against the whole transcript; reference notes are optional adjudication context. Do not present synthetic examples as independent clinician validation or benchmark scores as regulatory/clinical approval.

Offline tests, mock/human-judge paths and audits are distinct from external model evaluation. Live Anthropic judging sends inputs externally and can incur cost; optional medication terminology adds a FHIR service. Do not launch paid/live evaluation or transmit data without explicit applicable authority. Use synthetic/sanitised inputs; the tool does not de-identify data. Keep private reviewer identities, clinical transcripts, raw responses and secrets out of committed public evidence. Preserve Australian terminology and independent reviewer/adjudication provenance.

## Working agreement

Inspect current code, manifests and relevant task documents before editing. Complete the authorised task, including routine fixes and proportionate verification; carry forward prior approval without repeatedly asking. Delegate only bounded, independent work when useful, with explicit scope and authority. Stop at the requested scope. New spend, external writes, migrations, release, merge or deployment require applicable explicit authority; a plan or tool access does not grant it.

Keep changes small and reversible. Protect secrets, privacy, tenant isolation, access controls and audit integrity. Never use `any` for clinical, audit, tenant, identity or access-control data. Use synthetic or sanitised examples. Report changed files, checks passed, checks not run and residual risks. Distinguish implemented, release-ready and released using evidence for each. For documentation-only edits, verify paths, commands and `git diff --check`; do not install dependencies or run full application suites without a task-relevant reason.
