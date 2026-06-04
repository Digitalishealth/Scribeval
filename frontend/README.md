# Scribeval Demo Frontend

This is a static demo dashboard for reviewing synthetic Scribeval benchmark
outputs. It compares:

- Nurse + CDSS baseline documentation
- Four product-agnostic model candidates
- Four prompting strategies: standard, structured SOAP, safety-first, and
  CDSS-informed prompting

The data in `demo-data.json` is synthetic and exists to show how Scribeval
outputs can be presented for product-selection review. It is not a clinical
validation result.

## Run Locally

From the repository root:

```bash
python3 -m http.server 8765
```

Then open:

```text
http://localhost:8765/frontend/
```

The dashboard has no build step and no external JavaScript dependencies.
