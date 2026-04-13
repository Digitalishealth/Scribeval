# Contributing to Scribeval

Thank you for your interest in Scribeval. This project is a clinician-facing
evaluation framework, so contributions are welcome from both software
engineers and clinical reviewers.

## Ways to contribute

1. **Clinical rubric review** — the most valuable contribution. Read the YAML
   files in `rubrics/` and open an issue or PR if a severity criterion,
   example, or Australian-context reference is missing, incorrect, or
   out-of-date. You do not need to write Python to do this.
2. **New sample cases** — synthetic, clearly-planted consultation scenarios
   extend the benchmark corpus. See `samples/README.md` for the format.
3. **Bug fixes and features** — standard pull requests.
4. **Calibration data** — if you run an inter-rater reliability study against
   the LLM judge, share your de-identified rating pairs so we can improve the
   default rubrics.

## Scope and non-goals

Scribeval is deliberately narrow. Please read `METHODOLOGY.md` before
proposing a new dimension — several have already been considered and
rejected for documented reasons.

Non-goals:
- Scribeval will not ingest real patient data for any contributor workflow.
  All test data must be synthetic.
- Scribeval will not provide clinical advice, diagnosis, or regulatory
  certification. It is a quality-assurance tool.
- Scribeval will not bundle or fine-tune any private model. The judge layer
  is API-based and pluggable.

## Development setup

```bash
git clone <repo>
cd scribeval
pip install -e ".[dev]"
pytest
ruff check src/ tests/
```

## Pull request checklist

- [ ] Tests pass (`pytest`)
- [ ] Lint passes (`ruff check src/ tests/`)
- [ ] Rubric YAML files validate (`scribeval validate-rubric rubrics/<file>.yaml`)
- [ ] If you added a new evaluation dimension, `METHODOLOGY.md` includes the
      rationale and literature basis, and `DATA_FLOW.md` reflects any new
      external calls
- [ ] If you changed anything that affects scoring, tests that assert
      specific score values have been updated deliberately

## Reviewing rubrics as a clinician

You do not need a development environment to review rubrics. Open any YAML
file in `rubrics/` on GitHub and comment on lines you want changed. A
maintainer will translate your feedback into a PR.

The fields to focus on are:
- `severity_criteria` — are the thresholds clinically sensible?
- `examples` — are the examples realistic for Australian practice?
- `australian_context` — are the regulatory references current?
- `evaluation_instructions` — does the prompt ask the right questions?

## Code of conduct

Please be respectful. Clinical safety is a domain where disagreement is
normal and valuable — disagree with ideas, not people.
