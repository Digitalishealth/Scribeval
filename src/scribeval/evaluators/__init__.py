"""Evaluator registry and factory."""

from __future__ import annotations

from scribeval.evaluators.ahpra import AHPRAComplianceEvaluator
from scribeval.evaluators.base import BaseEvaluator
from scribeval.evaluators.hallucination import HallucinationEvaluator
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
}

DIMENSION_DESCRIPTIONS: dict[str, str] = {
    "omission": "Clinically significant information dropped from the note",
    "hallucination": "Fabricated or incorrect clinical information in the note",
    "medicolegal": "Whether documentation meets medicolegal protection standards",
    "ahpra": "Alignment with Medical Board of Australia / AHPRA standards",
    "pdqi9": "PDQI-9: 9-item validated note quality instrument (Stetson et al. 2012)",
    "qnote": "QNOTE: Domain-based clinical note quality instrument (Burke et al. 2014)",
}


def get_evaluator(
    dimension: str, rubric: RubricSchema, judge: BaseJudge
) -> BaseEvaluator:
    """Create an evaluator instance for the given dimension."""
    if dimension not in EVALUATOR_REGISTRY:
        available = ", ".join(sorted(EVALUATOR_REGISTRY.keys()))
        raise ValueError(f"Unknown dimension '{dimension}'. Available: {available}")
    cls = EVALUATOR_REGISTRY[dimension]
    return cls(rubric=rubric, judge=judge)


__all__ = [
    "EVALUATOR_REGISTRY",
    "DIMENSION_DESCRIPTIONS",
    "BaseEvaluator",
    "OmissionEvaluator",
    "HallucinationEvaluator",
    "MedicolegalEvaluator",
    "AHPRAComplianceEvaluator",
    "PDQI9Evaluator",
    "QNoteEvaluator",
    "get_evaluator",
]
