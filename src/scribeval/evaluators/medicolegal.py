"""Medicolegal evaluator: documentation against Australian medicolegal standards."""

from __future__ import annotations

from scribeval.evaluators.base import OUTPUT_SCHEMA, BaseEvaluator
from scribeval.models.case import EvaluationCase


class MedicolegalEvaluator(BaseEvaluator):
    """Evaluates medicolegal adequacy of clinical documentation."""

    dimension = "medicolegal"

    def build_prompt(self, case: EvaluationCase) -> str:
        rubric = self._format_rubric_section()
        inputs = self._format_inputs(case)

        return f"""\
You are evaluating an AI medical scribe's output for MEDICOLEGAL ADEQUACY — \
whether the clinical note meets Australian medicolegal documentation standards \
and would adequately protect the clinician in the event of a complaint, coronial \
inquest, or civil litigation.

Your assessment should be based on guidance from Australian medical defence \
organisations (Avant Mutual, MDA National, MIGA) and the Medical Board of \
Australia's Good Medical Practice code.

{rubric}

---

{inputs}

---

## Your Task

Assess the AI scribe output against the following medicolegal elements, \
considering what was actually discussed in the consultation:

1. CLINICAL REASONING: Is the thought process behind diagnosis and management \
documented or clearly inferable from the note?

2. INFORMED CONSENT: Are relevant consent discussions documented, particularly \
for procedures, off-label prescriptions, or significant treatment decisions?

3. RISK ASSESSMENT: For presentations with potential serious pathology, is the \
assessment and exclusion of dangerous diagnoses documented?

4. SAFETY-NETTING: Are return-to-care instructions or red flag warnings \
documented where clinically appropriate?

5. EXAMINATION DOCUMENTATION: Are relevant positive AND negative examination \
findings documented to support clinical reasoning?

6. MANAGEMENT PLAN: Is the plan clearly documented with rationale for \
treatment choices?

IMPORTANT: Only assess elements that are relevant to what was discussed in the \
consultation. If the clinician did not discuss informed consent, the scribe \
cannot document it — do not penalise for content absent from the transcript.

{OUTPUT_SCHEMA}"""
