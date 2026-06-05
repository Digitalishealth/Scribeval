# Reproducible Validation Corpus

This directory is the public, versioned corpus layer for Scribeval validation.
It turns the protocol in `validation_pack/README.md` into concrete case packets
that can be scored, reviewed, and re-run.

The current corpus is a bootstrap subset. It contains four complete synthetic
case packets and is designed to grow to the 20-case manifest in
`validation_pack/case_manifest.json`.

## Corpus Unit

Each case packet contains:

- a whole consultation transcript
- two to five blinded final-note submissions
- a declared note source for each submission
- a declared prompting strategy for each model-derived submission
- seeded safety-critical failure modes for audit and reviewer calibration

The scoring unit remains:

```text
whole transcript -> final note quality score
```

## Evidence Linkage

The files in `../evidence/` reference these case IDs and blinded submissions.
That creates an auditable trail:

```text
case packet -> Scribeval score -> clinician rating -> calibration statistic
```

The included evidence is synthetic and illustrative until independent clinician
ratings are collected.

