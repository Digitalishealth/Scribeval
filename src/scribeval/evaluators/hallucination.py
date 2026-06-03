"""Hallucination evaluator: detects fabricated clinical information in a note."""

from __future__ import annotations

from scribeval.evaluators.base import OUTPUT_SCHEMA, BaseEvaluator
from scribeval.models.case import EvaluationCase


class HallucinationEvaluator(BaseEvaluator):
    """Evaluates hallucinated or fabricated clinical content."""

    dimension = "hallucination"

    def build_prompt(self, case: EvaluationCase) -> str:
        rubric = self._format_rubric_section()
        inputs = self._format_inputs(case)

        return f"""\
You are evaluating a candidate final clinical note for CLINICAL HALLUCINATIONS — \
fabricated, incorrect, or unsupported clinical information that appears in the \
final note but was never said or implied in the consultation transcript.

This is the most safety-critical evaluation dimension. A hallucinated medication, \
diagnosis, or examination finding can directly cause patient harm.

{rubric}

---

{inputs}

---

## Your Task

Examine every clinical assertion in the candidate final note. For each assertion, \
verify whether it is supported by the consultation transcript.

An assertion is a hallucination if it:
1. States something never said or implied in the transcript
2. Contradicts what was actually said in the transcript
3. Fabricates specific details (medications, doses, findings, dates)

An assertion is NOT a hallucination if it:
1. Is a reasonable clinical inference from what was discussed
2. Is standard template language that does not misrepresent the consultation
3. Paraphrases transcript content without changing clinical meaning

For each hallucination, identify the exact note text, what the transcript \
actually says, and the potential clinical impact.

{OUTPUT_SCHEMA}"""
