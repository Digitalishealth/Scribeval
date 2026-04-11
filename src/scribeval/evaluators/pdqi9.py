"""PDQI-9 evaluator: Physician Documentation Quality Instrument (9-item).

Adapted from Stetson PD, Bakken S, Wrenn JO, Siegler EL. Assessing Electronic
Note Quality Using the Physician Documentation Quality Instrument (PDQI-9).
Applied Clinical Informatics. 2012;3(2):164-174.
"""

from __future__ import annotations

from scribeval.evaluators.base import BaseEvaluator
from scribeval.models.case import EvaluationCase

PDQI9_OUTPUT_SCHEMA = """\
Respond with ONLY a JSON object matching this exact schema:
{
  "score": <float 0.0-1.0, normalised from mean of 9 items: (mean-1)/4>,
  "confidence": <float 0.0-1.0>,
  "severity_summary": "<none|low|moderate|high|critical>",
  "reasoning": "<overall assessment of note quality across all 9 PDQI-9 items>",
  "findings": [
    {
      "description": "PDQI-9 Item 1 - Up-to-date: <score>/5. <rationale>",
      "severity": "<none|low|moderate|high|critical>",
      "transcript_excerpt": "<supporting excerpt from transcript, or null>",
      "note_excerpt": "<supporting excerpt from note, or null>",
      "clinical_impact": "<impact of quality issue, or null if score 4-5>"
    },
    {
      "description": "PDQI-9 Item 2 - Accurate: <score>/5. <rationale>",
      "severity": "...",
      "transcript_excerpt": "...",
      "note_excerpt": "...",
      "clinical_impact": "..."
    },
    ...
    <repeat for all 9 items>
  ]
}\
"""


class PDQI9Evaluator(BaseEvaluator):
    """Evaluates note quality using the PDQI-9 instrument."""

    dimension = "pdqi9"

    def build_prompt(self, case: EvaluationCase) -> str:
        rubric = self._format_rubric_section()
        inputs = self._format_inputs(case)

        return f"""\
You are evaluating an AI medical scribe's output using the PDQI-9 \
(Physician Documentation Quality Instrument), a validated 9-item \
instrument for assessing clinical note quality.

You must score the note on EACH of the 9 items using a 1-5 Likert scale, \
then compute an overall normalised score.

{rubric}

---

{inputs}

---

## Your Task

Score the AI scribe output on each of the 9 PDQI-9 items below. Use the \
consultation transcript as ground truth for accuracy and completeness. \
If a reference note is provided, use it as an additional quality benchmark.

For each item, provide:
- The item score (1-5)
- Specific evidence from the note supporting your score
- Clinical impact of any deficiency

THE 9 ITEMS:
1. UP-TO-DATE: Does the note reflect the current clinical state?
2. ACCURATE: Is clinical information factually correct per the transcript?
3. THOROUGH: Are all clinically relevant details included?
4. USEFUL: Would this note support another clinician's decision-making?
5. ORGANISED: Is the note logically structured and navigable?
6. COMPREHENSIBLE: Is it clearly written with appropriate clinical language?
7. SUCCINCT: Is it appropriately concise without losing clinical content?
8. SYNTHESISED: Does the assessment integrate findings into clinical reasoning?
9. INTERNALLY CONSISTENT: Is the note free of internal contradictions?

SCORING:
- Score each item 1-5 (1=not at all, 2=slightly, 3=somewhat, 4=mostly, 5=extremely)
- Calculate the mean of all 9 items
- Convert to 0-1 scale: normalised_score = (mean - 1) / 4
- Map severity: mean >= 4 = low, 3-4 = moderate, 2-3 = high, < 2 = critical
- Report each item as a separate finding

{PDQI9_OUTPUT_SCHEMA}"""
