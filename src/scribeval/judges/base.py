"""Abstract base class for evaluation judges."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseJudge(ABC):
    """Base class for judges that score evaluation prompts.

    A judge receives a fully-constructed evaluation prompt and returns
    a raw string response (expected to be JSON). The judge is agnostic
    to the evaluation dimension — it simply executes the prompt.
    """

    @property
    @abstractmethod
    def judge_type(self) -> str:
        """Identifier for this judge type (e.g., 'llm', 'manual')."""
        ...

    @property
    @abstractmethod
    def judge_model(self) -> str | None:
        """Model identifier, if applicable."""
        ...

    @abstractmethod
    def evaluate(self, prompt: str) -> str:
        """Execute an evaluation prompt and return the raw response."""
        ...
