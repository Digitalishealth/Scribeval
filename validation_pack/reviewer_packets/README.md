# Blinded Reviewer Packets

These packets are generated from the public validation corpus by:

```bash
python scripts/build_reviewer_packets.py
```

Each case packet contains the transcript and blinded candidate notes that a clinician reviewer needs for independent scoring. Coordinator-only fields such as source identity, prompting details, and seeded failure labels are kept in the corpus JSON and omitted from these packet files.

The note text is preserved verbatim. If a submitted note identifies its own workflow in the clinical prose, that prose remains visible because altering it would change the material being scored.
