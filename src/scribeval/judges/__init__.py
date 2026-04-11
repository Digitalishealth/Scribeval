"""Judge implementations for scoring evaluations."""

from scribeval.judges.base import BaseJudge
from scribeval.judges.llm import LLMJudge

__all__ = ["BaseJudge", "LLMJudge"]
