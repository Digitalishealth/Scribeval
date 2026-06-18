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
- [x] Clinician reviewer scoring guide included for transcript-to-note score,
      severity, and dimension anchoring.
- [x] Full 20-case synthetic validation corpus included with traceable
      transcript/note packets.
- [x] Full 20-case validation corpus can run directly through
      `scribeval benchmark`.
- [x] Generated blinded reviewer packets included for clinician scoring without
      coordinator-only corpus metadata.
- [x] Pseudonymous reviewer registry template and clinician review protocol
      included for independent rating provenance.
- [x] Reviewer assignment builder creates balanced reviewer-specific
      worksheets for blinded case-submission collection.
- [x] Independent clinician review readiness audit checks two qualified
      reviewers plus overall and dimension ratings per blinded case-submission
      before calibration import.
- [x] Validation corpus judge-score exporter produces importable Scribeval
      score JSON without transcript/note text or raw judge excerpts.
- [x] Validation review-run status summary tracks assignment, worksheet, and
      judge-score readiness with aggregate counts only.
- [x] Clinician reviewer reliability summary measures inter-rater agreement
      before judge-vs-clinician calibration claims.
- [x] Consensus clinician rating builder produces judge-vs-consensus pairs and
      adjudication flags for reviewer disagreement.
- [x] Adjudication packet builder creates blinded dispute worksheets without
      reviewer IDs or candidate source metadata.
- [x] Adjudication decision importer resolves disputed consensus rows with
      qualified adjudicator provenance.
- [x] Validation-claim readiness assessment applies protocol thresholds before
      treating a completed bundle as validation evidence.
- [x] Versioned evidence bundle builder produces review-run status, readiness,
      calibration, agreement, stratified summary, manifest, and source-hash
      artifacts, including blinded reviewer-material hashes, scoring-guide
      source hash, and reviewer assignment/adjudicated consensus source hashes
      when supplied.
- [x] Evidence-run audit verifies publishable bundles and rejects raw clinician
      CSV inputs.
- [x] Evidence-run index summarizes bundle coverage, claim readiness, and
      agreement minima for public review.
- [x] Synthetic evidence-run bundle committed as a reproducible workflow
      artifact with raw reviewer inputs excluded and claim-readiness set false.
- [x] Evidence bundles include aggregate adjudication-burden summaries by
      dimension, specialty, note source, prompt strategy, and failure mode.
- [x] Stratified validation evidence summary included across specialty, note
      source, prompt strategy, and safety-critical failure mode, including
      kappa/ICC agreement metrics where enough pairs exist.
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
python scripts/audit_validation_evidence_runs.py
scribeval list-dimensions
scribeval benchmark samples/benchmark_manifest.json \
    --dimensions omission,hallucination \
    --output public_smoke_benchmark \
    --format both
```

The final benchmark command requires `SCRIBEVAL_ANTHROPIC_API_KEY` for a live
LLM judge. Without an API key, run the test suite and rubric validation as the
offline smoke test.
