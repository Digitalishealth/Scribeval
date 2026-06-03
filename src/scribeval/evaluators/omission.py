"""Omission evaluator: detects clinically significant information dropped from a note."""

from __future__ import annotations

from scribeval.evaluators.base import OUTPUT_SCHEMA, BaseEvaluator
from scribeval.models.case import EvaluationCase


class OmissionEvaluator(BaseEvaluator):
    """Evaluates omission of clinically significant information."""

    dimension = "omission"

    def build_prompt(self, case: EvaluationCase) -> str:
        rubric = self._format_rubric_section()
        inputs = self._format_inputs(case)

        return f"""\
You are evaluating a candidate final clinical note for CLINICAL OMISSIONS — \
clinically significant information present in the consultation transcript \
that has been dropped from the final note.

{rubric}

---

{inputs}

---

## Your Task

Systematically go through the consultation transcript and identify every \
piece of clinically relevant information. For each piece, check whether it \
appears (verbatim or appropriately paraphrased) in the candidate final note.

Remember:
- Not all transcript content belongs in a clinical note. Social pleasantries, \
repeated information, and non-clinical conversation are appropriately excluded.
- Focus on clinically significant omissions only.
- Classify each omission by severity (critical, high, moderate, low).
- Consider the Australian clinical context (Medicare, PBS, RACGP standards).

{OUTPUT_SCHEMA}"""
