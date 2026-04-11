"""Abstract base evaluator and shared prompt/parsing logic."""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod

from scribeval.judges.base import BaseJudge
from scribeval.models.case import EvaluationCase
from scribeval.models.score import DimensionScore, Evidence, SeverityLevel
from scribeval.rubrics.loader import RubricSchema

OUTPUT_SCHEMA = """\
Respond with ONLY a JSON object matching this exact schema:
{
  "score": <float 0.0-1.0, where 1.0 = perfect>,
  "confidence": <float 0.0-1.0>,
  "severity_summary": "<none|low|moderate|high|critical>",
  "reasoning": "<your chain-of-thought reasoning>",
  "findings": [
    {
      "description": "<what was found>",
      "severity": "<none|low|moderate|high|critical>",
      "transcript_excerpt": "<relevant excerpt from transcript, or null>",
      "note_excerpt": "<relevant excerpt from scribe note, or null>",
      "clinical_impact": "<potential clinical impact, or null>"
    }
  ]
}\
"""


def _extract_json(text: str) -> str:
    """Extract JSON from text that may contain markdown fences."""
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


class BaseEvaluator(ABC):
    """Abstract base class for dimension-specific evaluators.

    Each evaluator constructs a prompt specific to its clinical safety
    dimension, sends it to a judge, and parses the structured response.
    """

    dimension: str = ""

    def __init__(self, rubric: RubricSchema, judge: BaseJudge):
        self.rubric = rubric
        self.judge = judge

    @abstractmethod
    def build_prompt(self, case: EvaluationCase) -> str:
        """Construct the evaluation prompt for this dimension."""
        ...

    def parse_response(self, raw_response: str) -> DimensionScore:
        """Parse the judge's JSON response into a DimensionScore."""
        json_str = _extract_json(raw_response)
        data = json.loads(json_str)

        findings = [
            Evidence(
                description=f["description"],
                severity=SeverityLevel(f["severity"]),
                transcript_excerpt=f.get("transcript_excerpt"),
                note_excerpt=f.get("note_excerpt"),
                clinical_impact=f.get("clinical_impact"),
            )
            for f in data.get("findings", [])
        ]

        return DimensionScore(
            dimension=self.dimension,
            score=float(data["score"]),
            confidence=float(data["confidence"]),
            severity_summary=SeverityLevel(data["severity_summary"]),
            findings=findings,
            reasoning=data["reasoning"],
            rubric_version=self.rubric.version,
            judge_type=self.judge.judge_type,
            judge_model=self.judge.judge_model,
            raw_judge_response=raw_response,
        )

    def evaluate(self, case: EvaluationCase) -> DimensionScore:
        """Run the full evaluation: build prompt -> judge -> parse."""
        prompt = self.build_prompt(case)
        raw_response = self.judge.evaluate(prompt)
        return self.parse_response(raw_response)

    def _format_rubric_section(self) -> str:
        """Format the rubric's severity criteria and instructions for the prompt."""
        sections = []
        sections.append(f"## Evaluation Dimension: {self.rubric.display_name}")
        sections.append(f"\n{self.rubric.description.strip()}")

        sections.append("\n## Severity Criteria")
        for level, criterion in self.rubric.severity_criteria.items():
            sections.append(f"\n### {level.upper()}")
            sections.append(criterion.description.strip())
            if criterion.examples:
                for ex in criterion.examples:
                    sections.append(f"  - {ex}")

        instructions = self.rubric.evaluation_instructions.strip()
        sections.append(f"\n## Evaluation Instructions\n{instructions}")
        sections.append(
            f"\n## Australian Context\n{self.rubric.australian_context.strip()}"
        )

        return "\n".join(sections)

    def _format_inputs(self, case: EvaluationCase) -> str:
        """Format the case inputs for the prompt."""
        parts = []
        parts.append("## Consultation Transcript")
        parts.append(f"```\n{case.transcript.content}\n```")
        parts.append("\n## AI Scribe Output Note")
        parts.append(f"```\n{case.scribe_note.content}\n```")

        if case.reference_note:
            parts.append("\n## Reference Note (Gold Standard)")
            parts.append(f"```\n{case.reference_note.content}\n```")

        return "\n".join(parts)
