"""Evaluator registry and factory."""

from __future__ import annotations

from typing import Any

from scribeval.evaluators.ahpra import AHPRAComplianceEvaluator
from scribeval.evaluators.base import BaseEvaluator
from scribeval.evaluators.hallucination import HallucinationEvaluator
from scribeval.evaluators.medication_terminology import (
    MedicationTerminologyEvaluator,
)
from scribeval.evaluators.medicolegal import MedicolegalEvaluator
from scribeval.evaluators.omission import OmissionEvaluator
from scribeval.evaluators.pdqi9 import PDQI9Evaluator
from scribeval.evaluators.qnote import QNoteEvaluator
from scribeval.judges.base import BaseJudge
from scribeval.rubrics.loader import RubricSchema

EVALUATOR_REGISTRY: dict[str, type[BaseEvaluator]] = {
    "omission": OmissionEvaluator,
    "hallucination": HallucinationEvaluator,
    "medicolegal": MedicolegalEvaluator,
    "ahpra": AHPRAComplianceEvaluator,
    "pdqi9": PDQI9Evaluator,
    "qnote": QNoteEvaluator,
    "medication_terminology": MedicationTerminologyEvaluator,
}

DIMENSION_DESCRIPTIONS: dict[str, str] = {
    "omission": "Clinically significant information dropped from the note",
    "hallucination": "Fabricated or incorrect clinical information in the note",
    "medicolegal": "Whether documentation meets medicolegal protection standards",
    "ahpra": "Alignment with Medical Board of Australia / AHPRA standards",
    "pdqi9": "PDQI-9: 9-item validated note quality instrument (Stetson et al. 2012)",
    "qnote": "QNOTE: Domain-based clinical note quality instrument (Burke et al. 2014)",
    "medication_terminology": (
        "AMT validation of medication names via FHIR (opt-in, requires "
        "configurable terminology server). Catches non-existent or imprecise "
        "drug names. Australian-specific."
    ),
}

# Dimensions that are not in the default suite — must be explicitly opted in.
OPT_IN_DIMENSIONS: set[str] = {"medication_terminology"}


def get_evaluator(
    dimension: str,
    rubric: RubricSchema,
    judge: BaseJudge,
    **kwargs: Any,
) -> BaseEvaluator:
    """Create an evaluator instance for the given dimension.

    Some evaluators (e.g., medication_terminology) accept additional
    constructor arguments via kwargs. Unknown kwargs are silently ignored
    by evaluators that do not accept them.
    """
    if dimension not in EVALUATOR_REGISTRY:
        available = ", ".join(sorted(EVALUATOR_REGISTRY.keys()))
        raise ValueError(f"Unknown dimension '{dimension}'. Available: {available}")
    cls = EVALUATOR_REGISTRY[dimension]

    if dimension == "medication_terminology":
        return cls(
            rubric=rubric,
            judge=judge,
            fhir_client=kwargs.get("fhir_client"),
        )
    return cls(rubric=rubric, judge=judge)


__all__ = [
    "EVALUATOR_REGISTRY",
    "DIMENSION_DESCRIPTIONS",
    "OPT_IN_DIMENSIONS",
    "BaseEvaluator",
    "OmissionEvaluator",
    "HallucinationEvaluator",
    "MedicolegalEvaluator",
    "AHPRAComplianceEvaluator",
    "PDQI9Evaluator",
    "QNoteEvaluator",
    "MedicationTerminologyEvaluator",
    "get_evaluator",
]
