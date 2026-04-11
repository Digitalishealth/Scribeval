"""Evaluator registry and factory."""

from __future__ import annotations

from scribeval.evaluators.ahpra import AHPRAComplianceEvaluator
from scribeval.evaluators.base import BaseEvaluator
from scribeval.evaluators.hallucination import HallucinationEvaluator
from scribeval.evaluators.medicolegal import MedicolegalEvaluator
from scribeval.evaluators.omission import OmissionEvaluator
from scribeval.judges.base import BaseJudge
from scribeval.rubrics.loader import RubricSchema

EVALUATOR_REGISTRY: dict[str, type[BaseEvaluator]] = {
    "omission": OmissionEvaluator,
    "hallucination": HallucinationEvaluator,
    "medicolegal": MedicolegalEvaluator,
    "ahpra": AHPRAComplianceEvaluator,
}

DIMENSION_DESCRIPTIONS: dict[str, str] = {
    "omission": "Clinically significant information dropped from the note",
    "hallucination": "Fabricated or incorrect clinical information in the note",
    "medicolegal": "Whether documentation meets medicolegal protection standards",
    "ahpra": "Alignment with Medical Board of Australia / AHPRA standards",
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
    "get_evaluator",
]
