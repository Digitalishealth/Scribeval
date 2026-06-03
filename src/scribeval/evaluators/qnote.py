"""QNOTE evaluator: Quality of Clinical Notes instrument.

Adapted from Burke HB, Sessums LL, Hoang A, et al. QNOTE: An instrument for
measuring the quality of EHR clinical notes. JAMIA. 2014;21(5):910-916.
"""

from __future__ import annotations

from scribeval.evaluators.base import BaseEvaluator
from scribeval.models.case import EvaluationCase

QNOTE_OUTPUT_SCHEMA = """\
Respond with ONLY a JSON object matching this exact schema:
{
  "score": <float 0.0-1.0, normalised from mean of scored domains: (mean-1)/4>,
  "confidence": <float 0.0-1.0>,
  "severity_summary": "<none|low|moderate|high|critical>",
  "reasoning": "<overall assessment across all QNOTE domains>",
  "findings": [
    {
      "description": "QNOTE Domain 1 - Presenting Complaint: <score>/5. <rationale>",
      "severity": "<none|low|moderate|high|critical>",
      "transcript_excerpt": "<supporting excerpt from transcript, or null>",
      "note_excerpt": "<supporting excerpt from note, or null>",
      "clinical_impact": "<impact of quality issue, or null if score 4-5>"
    },
    {
      "description": "QNOTE Domain 2 - History of Presenting Illness: <score>/5. <rationale>",
      "severity": "...",
      "transcript_excerpt": "...",
      "note_excerpt": "...",
      "clinical_impact": "..."
    },
    ...
    <repeat for all 8 domains, marking N/A domains as severity "none" with \
description explaining why N/A>
  ]
}\
"""


class QNoteEvaluator(BaseEvaluator):
    """Evaluates note quality using the QNOTE instrument."""

    dimension = "qnote"

    def build_prompt(self, case: EvaluationCase) -> str:
        rubric = self._format_rubric_section()
        inputs = self._format_inputs(case)

        return f"""\
You are evaluating a candidate final clinical note using QNOTE (Quality of \
Clinical Notes), a validated instrument for measuring clinical note quality \
across structured documentation domains.

You must score the note on each applicable domain using a 1-5 scale, \
then compute an overall normalised score.

{rubric}

---

{inputs}

---

## Your Task

Evaluate the candidate final note across all 8 QNOTE domains. Use the \
consultation transcript as ground truth. If a reference note is provided, \
use it as an additional quality benchmark.

THE 8 DOMAINS:

1. PRESENTING COMPLAINT / REASON FOR VISIT:
   Is the reason for the consultation clearly and specifically stated?
   (1=absent/wrong, 2=vague, 3=present but generic, 4=clear and specific, \
5=exemplary)

2. HISTORY OF PRESENTING ILLNESS (HPI):
   Does the note capture onset, duration, severity, character, associated \
symptoms, exacerbating/relieving factors?
   (1=absent/wrong, 2=minimal, 3=partial, 4=comprehensive, 5=exemplary)

3. PAST MEDICAL/SURGICAL HISTORY:
   Are relevant past conditions documented? Score N/A if not discussed and \
not relevant.
   (1=absent when relevant, 2=minimal, 3=partial, 4=well-documented, \
5=exemplary)

4. MEDICATIONS AND ALLERGIES (SAFETY-CRITICAL):
   Are medications accurate with doses? Are allergies documented? Are new \
prescriptions noted with indication?
   (1=absent/wrong, 2=incomplete with errors, 3=partial, 4=comprehensive, \
5=exemplary)

5. REVIEW OF SYSTEMS:
   If conducted, is it documented with pertinent positives and negatives? \
Score N/A if not performed.
   (1=absent when conducted, 2=minimal, 3=partial, 4=well-documented, \
5=exemplary)

6. PHYSICAL EXAMINATION:
   Are findings accurate, specific, with pertinent negatives? Score N/A if \
not performed (e.g., telehealth).
   (1=absent/wrong, 2=minimal, 3=partial, 4=comprehensive, 5=exemplary)

7. ASSESSMENT AND PLAN (SAFETY-CRITICAL):
   Does assessment reflect clinical reasoning? Is the plan specific, \
actionable, with safety-netting?
   (1=absent/wrong, 2=vague, 3=present but incomplete, 4=clear and \
comprehensive, 5=exemplary)

8. OVERALL NOTE QUALITY:
   Holistic assessment — coherence, readability, fitness for purpose.
   (1=clinically unsafe, 2=poor, 3=adequate, 4=good, 5=excellent)

SCORING RULES:
- For domains scored N/A, exclude from the mean calculation.
- Calculate mean of all scored domains (1-5 scale).
- Convert to 0-1: normalised_score = (mean - 1) / 4
- Domains 4 (Medications/Allergies) and 7 (Assessment/Plan) are SAFETY-CRITICAL. \
Any deficiency (score <= 3) in these domains should be flagged at HIGH severity \
minimum, regardless of overall score.
- Report each domain as a separate finding.

{QNOTE_OUTPUT_SCHEMA}"""
