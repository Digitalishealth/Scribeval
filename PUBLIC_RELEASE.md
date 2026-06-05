# Public Release Checklist

Scribeval is intended to be a publicly available code stack for comparing the
clinical quality and safety of AI scribe outputs against consultation
transcripts.

## Code Readiness

- [x] Open-source licence present (`LICENSE`, MIT).
- [x] Medical-device and clinical-validation disclaimers present in README and
      report models.
- [x] Data-flow disclosure documented, including Anthropic and optional FHIR
      terminology server flows.
- [x] Synthetic sample cases included; no real patient data is committed.
- [x] Single-case transcript-to-note scoring available via `scribeval evaluate`.
- [x] Single-case blinded GP-vs-AI/product comparison available via
      `scribeval compare`.
- [x] Multi-case product benchmark aggregation available via
      `scribeval benchmark`.
- [x] Static demo frontend available for synthetic Nurse + CDSS versus model
      comparison outputs.
- [x] Clinician validation pilot pack included with blinded reviewer worksheet
      and example calibration output.
- [x] Validation corpus audit verifies case packets and evidence references
      without API keys.
- [x] JSON and Markdown outputs available for audit and governance review.
- [x] Tests and lint pass locally.
- [x] Public release audit script scans for obvious committed secrets and
      private data markers.
- [x] CI runs tests, lint, and rubric validation on all pushed branches and pull
      requests.

## Publication Steps

- [x] Review all files for accidental secrets, private URLs, or real clinical
      data before changing repository visibility.
- [x] Decide whether to keep the current default branch name or rename the
      public default branch to `main`.
- [x] Make `Digitalishealth/Scribeval` public on GitHub.
- [x] Push the release branch and confirm GitHub Actions pass on the public
      repository.
- [x] Confirm the public demo loads at
      `https://digitalishealth.github.io/Scribeval/`.
- [ ] Optional: create a GitHub release tag and attach the recommended quick-start
      command from `README.md`.

## Recommended Public Smoke Test

After publishing, clone the repository into a fresh directory and run:

```bash
pip install -e ".[dev]"
pytest -q
ruff check src tests
python scripts/public_release_audit.py
scribeval list-dimensions
scribeval benchmark samples/benchmark_manifest.json \
    --dimensions omission,hallucination \
    --output public_smoke_benchmark \
    --format both
```

The final benchmark command requires `SCRIBEVAL_ANTHROPIC_API_KEY` for a live
LLM judge. Without an API key, run the test suite and rubric validation as the
offline smoke test.
