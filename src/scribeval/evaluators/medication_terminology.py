"""Medication Terminology evaluator: validates drug names against AMT via FHIR.

This is a two-phase evaluator that diverges from the pure LLM-as-judge pattern:
1. Extraction phase: the LLM judge extracts medication mentions from the
   candidate final note (drug name, strength, form).
2. Validation phase: each extracted medication is validated against the
   Australian Medicines Terminology (AMT) via a configurable FHIR R4
   terminology server.

This evaluator catches a narrow class of errors (non-existent or imprecise
drug names) that LLM-only evaluators may miss. It does NOT assess clinical
appropriateness — see the rubric for full limitations.

Privacy: only extracted medication strings are sent to the FHIR server.
Consultation transcripts, patient identifiers, and other clinical context
are never transmitted to the FHIR endpoint.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from scribeval.clients.fhir import (
    FHIRTerminologyClient,
    FHIRUnreachableError,
    ValidationOutcome,
    ValidationResult,
)
from scribeval.evaluators.base import BaseEvaluator, _extract_json
from scribeval.judges.base import BaseJudge
from scribeval.models.case import EvaluationCase
from scribeval.models.score import DimensionScore, Evidence, SeverityLevel
from scribeval.rubrics.loader import RubricSchema

# Per-item scores by validation outcome
OUTCOME_SCORES: dict[ValidationOutcome, float] = {
    ValidationOutcome.VALID_EXACT: 1.0,
    ValidationOutcome.VALID_VARIANT: 0.9,
    ValidationOutcome.VALID_LESS_SPECIFIC: 0.6,
    ValidationOutcome.AMBIGUOUS: 0.3,
    ValidationOutcome.INVALID: 0.0,
    ValidationOutcome.LOOKUP_FAILED: 0.0,
}

# Severity classification by outcome
OUTCOME_SEVERITY: dict[ValidationOutcome, SeverityLevel] = {
    ValidationOutcome.VALID_EXACT: SeverityLevel.NONE,
    ValidationOutcome.VALID_VARIANT: SeverityLevel.LOW,
    ValidationOutcome.VALID_LESS_SPECIFIC: SeverityLevel.MODERATE,
    ValidationOutcome.AMBIGUOUS: SeverityLevel.HIGH,
    ValidationOutcome.INVALID: SeverityLevel.CRITICAL,
    ValidationOutcome.LOOKUP_FAILED: SeverityLevel.LOW,
}

EXTRACTION_PROMPT_TEMPLATE = """\
You are extracting medication mentions from a candidate final clinical \
note for terminology validation. Your job is purely extractive — do NOT \
evaluate, judge, or modify the medications.

## Candidate Final Note

```
{note}
```

## Your Task

Extract every distinct medication mention from the note above. For each \
medication, capture:
- name: the drug name as written in the note (e.g., "amoxicillin")
- strength: the strength/dose if specified (e.g., "500mg"), or null
- form: the dose form if specified (e.g., "tablet", "syrup"), or null
- context: where it appears ("current_medications", "new_prescription", \
"history", "other")

Rules:
- Include both new prescriptions and current medications.
- Do NOT include allergies (those are not medications being taken).
- Do NOT include vaccines unless they are being prescribed in this consultation.
- If the same medication appears multiple times, include it only once.
- If no medications appear in the note, return an empty list.

Respond with ONLY a JSON object matching this exact schema:
{{
  "medications": [
    {{
      "name": "<drug name>",
      "strength": "<strength or null>",
      "form": "<form or null>",
      "context": "<current_medications|new_prescription|history|other>"
    }}
  ]
}}\
"""


@dataclass
class ExtractedMedication:
    name: str
    strength: str | None
    form: str | None
    context: str

    def query_string(self) -> str:
        """Build the string sent to the FHIR server for validation."""
        parts = [self.name]
        if self.strength:
            parts.append(self.strength)
        if self.form:
            parts.append(self.form)
        return " ".join(parts).strip()


class MedicationTerminologyEvaluator(BaseEvaluator):
    """Two-phase evaluator: LLM extracts medications, FHIR validates against AMT.

    This evaluator overrides the standard `evaluate()` method because it
    does not follow the single-prompt LLM-as-judge pattern. The build_prompt
    method is implemented for compatibility but is not used by evaluate().
    """

    dimension = "medication_terminology"

    def __init__(
        self,
        rubric: RubricSchema,
        judge: BaseJudge,
        fhir_client: FHIRTerminologyClient | None = None,
    ):
        super().__init__(rubric=rubric, judge=judge)
        self.fhir_client = fhir_client

    def build_prompt(self, case: EvaluationCase) -> str:
        """Build the extraction prompt (phase 1 only).

        This evaluator does not use the standard single-prompt flow, but
        we implement build_prompt for interface compatibility and so the
        extraction prompt is inspectable.
        """
        return EXTRACTION_PROMPT_TEMPLATE.format(note=case.scribe_note.content)

    def evaluate(self, case: EvaluationCase) -> DimensionScore:
        """Run two-phase evaluation: extract medications, then validate against AMT."""
        if self.fhir_client is None:
            return self._degraded_score(
                "FHIR client not configured. Set SCRIBEVAL_FHIR_TERMINOLOGY_URL "
                "and ensure scribeval was instantiated with a FHIR client."
            )

        # Phase 1: extract medications via LLM
        extraction_prompt = self.build_prompt(case)
        raw_extraction = self.judge.evaluate(extraction_prompt)
        try:
            medications = self._parse_extraction(raw_extraction)
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            return self._degraded_score(
                f"Failed to parse medication extraction response: {exc}",
                raw_response=raw_extraction,
            )

        if not medications:
            return DimensionScore(
                dimension=self.dimension,
                score=1.0,
                confidence=1.0,
                severity_summary=SeverityLevel.NONE,
                findings=[
                    Evidence(
                        description="No medications found in candidate note to validate.",
                        severity=SeverityLevel.NONE,
                    )
                ],
                reasoning=(
                    "The candidate note contains no medication mentions. "
                    "No AMT validation was required."
                ),
                rubric_version=self.rubric.version,
                judge_type=self.judge.judge_type,
                judge_model=self.judge.judge_model,
                raw_judge_response=raw_extraction,
            )

        # Phase 2: validate each medication against AMT via FHIR
        try:
            results = self._validate_medications(medications)
        except FHIRUnreachableError as exc:
            return self._degraded_score(
                f"FHIR endpoint unreachable: {exc}",
                raw_response=raw_extraction,
            )

        return self._build_score(results, raw_extraction)

    def _parse_extraction(self, raw: str) -> list[ExtractedMedication]:
        """Parse the LLM extraction response into ExtractedMedication objects."""
        json_str = _extract_json(raw)
        data = json.loads(json_str)
        meds = data.get("medications", [])
        if not isinstance(meds, list):
            raise TypeError(f"Expected 'medications' to be a list, got {type(meds)}")
        return [
            ExtractedMedication(
                name=str(m["name"]).strip(),
                strength=(m.get("strength") or None),
                form=(m.get("form") or None),
                context=str(m.get("context", "other")),
            )
            for m in meds
            if m.get("name")
        ]

    def _validate_medications(
        self, medications: list[ExtractedMedication]
    ) -> list[tuple[ExtractedMedication, ValidationResult]]:
        """Validate each extracted medication against AMT.

        Raises FHIRUnreachableError if the endpoint cannot be reached at all.
        Individual lookup failures are captured per-medication, not raised.
        """
        assert self.fhir_client is not None
        results = []
        for med in medications:
            # Use the bare drug name for FHIR lookup — strength/form are
            # informational only and reduce match rates if included verbatim
            result = self.fhir_client.validate_medication(med.name)
            results.append((med, result))
        return results

    def _build_score(
        self,
        results: list[tuple[ExtractedMedication, ValidationResult]],
        raw_response: str,
    ) -> DimensionScore:
        """Compute the dimension score from validation results."""
        per_item_scores = [OUTCOME_SCORES[r.outcome] for _, r in results]
        mean_score = sum(per_item_scores) / len(per_item_scores)

        # Cap at 0.5 if any medication is critical (invalid)
        has_critical = any(
            r.outcome == ValidationOutcome.INVALID for _, r in results
        )
        if has_critical:
            mean_score = min(mean_score, 0.5)

        findings = [
            self._build_finding(med, result) for med, result in results
        ]

        # Confidence reflects how many lookups succeeded
        success_count = sum(
            1 for _, r in results if r.outcome != ValidationOutcome.LOOKUP_FAILED
        )
        confidence = success_count / len(results) if results else 0.0

        worst_severity = self._worst_severity(
            [OUTCOME_SEVERITY[r.outcome] for _, r in results]
        )

        reasoning = self._build_reasoning(results, mean_score)

        return DimensionScore(
            dimension=self.dimension,
            score=round(mean_score, 4),
            confidence=round(confidence, 4),
            severity_summary=worst_severity,
            findings=findings,
            reasoning=reasoning,
            rubric_version=self.rubric.version,
            judge_type=self.judge.judge_type,
            judge_model=self.judge.judge_model,
            raw_judge_response=raw_response,
        )

    def _build_finding(
        self, med: ExtractedMedication, result: ValidationResult
    ) -> Evidence:
        severity = OUTCOME_SEVERITY[result.outcome]
        description = self._format_finding_description(med, result)
        clinical_impact = self._clinical_impact_for_outcome(result.outcome)
        return Evidence(
            description=description,
            severity=severity,
            note_excerpt=med.query_string(),
            clinical_impact=clinical_impact,
        )

    def _format_finding_description(
        self, med: ExtractedMedication, result: ValidationResult
    ) -> str:
        base = f"Medication '{med.name}'"
        if med.strength:
            base += f" {med.strength}"

        outcome_text = {
            ValidationOutcome.VALID_EXACT: "validates exactly against AMT",
            ValidationOutcome.VALID_VARIANT: "validates as an acceptable AMT variant",
            ValidationOutcome.VALID_LESS_SPECIFIC: (
                "validates against AMT but a more specific concept exists"
            ),
            ValidationOutcome.AMBIGUOUS: (
                "matches multiple AMT concepts — disambiguation needed"
            ),
            ValidationOutcome.INVALID: "does NOT validate against AMT",
            ValidationOutcome.LOOKUP_FAILED: "could not be validated (lookup failed)",
        }[result.outcome]

        suffix = ""
        if result.matched_display and result.outcome != ValidationOutcome.VALID_EXACT:
            suffix = f" (closest AMT match: '{result.matched_display}')"
        elif result.message:
            suffix = f" — {result.message}"

        return f"{base} {outcome_text}{suffix}"

    def _clinical_impact_for_outcome(
        self, outcome: ValidationOutcome
    ) -> str | None:
        if outcome == ValidationOutcome.INVALID:
            return (
                "Medication name does not exist in AMT. May indicate a "
                "fabricated drug, serious misspelling, or non-existent product. "
                "Could lead to prescribing error or wrong-drug administration."
            )
        if outcome == ValidationOutcome.AMBIGUOUS:
            return (
                "Medication name is ambiguous in AMT. Risk of wrong-strength "
                "or wrong-formulation dispensing if acted on without clarification."
            )
        if outcome == ValidationOutcome.VALID_LESS_SPECIFIC:
            return (
                "More specific AMT concept available. Documentation could be "
                "more precise for clinical handover and prescribing."
            )
        if outcome == ValidationOutcome.LOOKUP_FAILED:
            return (
                "Validation could not be performed due to a lookup failure. "
                "This medication has not been validated against AMT."
            )
        return None

    def _worst_severity(self, severities: list[SeverityLevel]) -> SeverityLevel:
        order = list(SeverityLevel)
        worst = SeverityLevel.NONE
        for s in severities:
            if order.index(s) > order.index(worst):
                worst = s
        return worst

    def _build_reasoning(
        self,
        results: list[tuple[ExtractedMedication, ValidationResult]],
        score: float,
    ) -> str:
        total = len(results)
        outcomes: dict[ValidationOutcome, int] = {}
        for _, r in results:
            outcomes[r.outcome] = outcomes.get(r.outcome, 0) + 1

        parts = [
            f"Extracted {total} medication mention(s) from the candidate note. "
            f"Validated each against AMT via FHIR $expand."
        ]
        for outcome, count in outcomes.items():
            parts.append(f"  - {outcome.value}: {count}")

        if any(r.outcome == ValidationOutcome.INVALID for _, r in results):
            parts.append(
                "Score capped at 0.5 because at least one medication did not "
                "validate (potential safety event)."
            )

        parts.append(f"Final dimension score: {score:.2f}/1.00")
        parts.append(
            "NOTE: This evaluator validates terminology only, not clinical "
            "appropriateness. A drug may validate against AMT but still be "
            "wrong for the patient or context."
        )
        return "\n".join(parts)

    def _degraded_score(
        self, message: str, raw_response: str | None = None
    ) -> DimensionScore:
        """Return a graceful-degradation score when validation cannot proceed."""
        return DimensionScore(
            dimension=self.dimension,
            score=0.0,
            confidence=0.0,
            severity_summary=SeverityLevel.LOW,
            findings=[
                Evidence(
                    description=message,
                    severity=SeverityLevel.LOW,
                    clinical_impact=(
                        "Medication terminology could not be validated. "
                        "Other dimensions remain valid; consider re-running "
                        "this dimension with a working FHIR endpoint."
                    ),
                )
            ],
            reasoning=(
                f"Medication terminology evaluation degraded: {message}\n"
                "Score set to 0.0 with confidence 0.0. Other evaluators are "
                "unaffected."
            ),
            rubric_version=self.rubric.version,
            judge_type=self.judge.judge_type,
            judge_model=self.judge.judge_model,
            raw_judge_response=raw_response,
        )


# Re-export for tests that want to construct expectations
__all__ = [
    "MedicationTerminologyEvaluator",
    "ExtractedMedication",
    "OUTCOME_SCORES",
    "OUTCOME_SEVERITY",
    "EXTRACTION_PROMPT_TEMPLATE",
]


# Sanity check: medication name must contain only safe characters before
# being sent to FHIR. Reject anything that looks like injection or PHI.
_SAFE_MED_PATTERN = re.compile(r"^[A-Za-z0-9 \-/\.\+()%,]+$")


def is_safe_medication_string(s: str) -> bool:
    """Return True if a string is safe to send to a FHIR terminology server.

    This is a defence-in-depth check: medication names should be short,
    plain alphanumeric strings. Anything else may indicate prompt injection
    or accidental inclusion of patient identifiers.
    """
    if not s or len(s) > 200:
        return False
    return bool(_SAFE_MED_PATTERN.match(s))
