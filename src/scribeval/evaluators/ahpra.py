"""AHPRA compliance evaluator: assesses alignment with Medical Board of Australia standards."""

from __future__ import annotations

from scribeval.evaluators.base import OUTPUT_SCHEMA, BaseEvaluator
from scribeval.models.case import EvaluationCase


class AHPRAComplianceEvaluator(BaseEvaluator):
    """Evaluates compliance with AHPRA and Medical Board of Australia standards."""

    dimension = "ahpra"

    def build_prompt(self, case: EvaluationCase) -> str:
        rubric = self._format_rubric_section()
        inputs = self._format_inputs(case)

        return f"""\
You are evaluating a candidate final clinical note for AHPRA COMPLIANCE — \
alignment with the Australian Health Practitioner Regulation Agency standards \
and the Medical Board of Australia's Good Medical Practice code of conduct.

This assessment focuses on whether the documentation meets the professional \
obligations set out in the Health Practitioner Regulation National Law and \
the Medical Board's guidelines on record-keeping.

{rubric}

---

{inputs}

---

## Your Task

Assess the candidate final note against the following AHPRA-relevant areas, \
considering what was discussed in the consultation:

1. RECORD-KEEPING (Good Medical Practice 8.4):
   - Are the records clear, accurate, and would they be considered contemporaneous?
   - Do they include relevant clinical findings, decisions, and actions?
   - Is the information sufficient for another practitioner to continue care?

2. COMMUNICATION AND CONSENT (Good Medical Practice 3.3-3.5):
   - Is shared decision-making reflected where it was discussed?
   - Are patient preferences and concerns documented?
   - Is informed consent documented for relevant decisions?

3. CULTURAL SAFETY (Good Medical Practice 4.5):
   - Are cultural considerations documented where relevant?
   - Is respectful, person-centred language used throughout?
   - Are Aboriginal and Torres Strait Islander health considerations \
addressed where relevant?

4. MANDATORY REPORTING (National Law Section 141):
   - If any mandatory reporting triggers were discussed, are they \
appropriately flagged in the documentation?

5. PRIVACY AND CONFIDENTIALITY (Good Medical Practice 4.10):
   - Does the note appropriately handle sensitive information?
   - Are third-party disclosures handled appropriately?

IMPORTANT: Only assess elements relevant to the actual consultation content. \
Not every consultation involves cultural safety or mandatory reporting triggers.

{OUTPUT_SCHEMA}"""
