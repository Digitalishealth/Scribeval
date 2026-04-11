"""LLM judge implementation using Anthropic Claude."""

from __future__ import annotations

import json
import re

import anthropic

from scribeval.judges.base import BaseJudge

SYSTEM_PROMPT = """\
You are an expert clinical documentation auditor with deep knowledge of \
Australian healthcare standards including AHPRA requirements, RACGP standards, \
Medicare/PBS documentation requirements, and medicolegal best practices.

You evaluate AI medical scribe outputs with rigorous attention to clinical \
safety. You are precise, evidence-based, and conservative in your assessments — \
you would rather flag a potential issue than miss a genuine clinical safety concern.

You MUST respond with valid JSON matching the schema specified in the prompt. \
Do not include any text outside the JSON object.\
"""


class LLMJudge(BaseJudge):
    """Anthropic Claude as an evaluation judge."""

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        api_key: str | None = None,
        max_retries: int = 2,
    ):
        self._model = model
        self._max_retries = max_retries
        self._client = anthropic.Anthropic(api_key=api_key)

    @property
    def judge_type(self) -> str:
        return "llm"

    @property
    def judge_model(self) -> str:
        return self._model

    def evaluate(self, prompt: str) -> str:
        """Send evaluation prompt to Claude and return the response."""
        response = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text

        # Validate JSON and retry if malformed
        for attempt in range(self._max_retries):
            try:
                json.loads(self._extract_json(raw))
                return raw
            except (json.JSONDecodeError, ValueError):
                if attempt < self._max_retries - 1:
                    retry_response = self._client.messages.create(
                        model=self._model,
                        max_tokens=4096,
                        system=SYSTEM_PROMPT,
                        messages=[
                            {"role": "user", "content": prompt},
                            {"role": "assistant", "content": raw},
                            {
                                "role": "user",
                                "content": (
                                    "Your response was not valid JSON. "
                                    "Please respond with ONLY a valid JSON object "
                                    "matching the requested schema."
                                ),
                            },
                        ],
                    )
                    raw = retry_response.content[0].text

        return raw

    @staticmethod
    def _extract_json(text: str) -> str:
        """Extract JSON from a response that may contain markdown fences."""
        # Try to find JSON in code blocks first
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if match:
            return match.group(1).strip()
        # Otherwise assume the whole response is JSON
        return text.strip()
