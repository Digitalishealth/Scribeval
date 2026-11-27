"""Offline regression checks for human-readable report governance fields."""

import unittest
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from scribeval.models.report import DimensionRunStatistics, EvaluationReport
from scribeval.models.score import DimensionScore, SeverityLevel
from scribeval.reporting.markdown_report import render_markdown
from scribeval.reproducibility import ReproducibilityMetadata, content_hash


def synthetic_report() -> EvaluationReport:
    """Mechanical rendering fixture; not clinician or model evaluation."""
    return EvaluationReport(
        report_id="synthetic-rendering-only",
        case_id="synthetic-case",
        consultation_type="synthetic",
        timestamp=datetime(2026, 11, 27, tzinfo=UTC),
        dimension_scores=[
            DimensionScore(
                dimension="omission",
                score=0.7,
                confidence=0.5,
                severity_summary=SeverityLevel.MODERATE,
                reasoning="Synthetic fixture only; no clinical review performed.",
                rubric_version="synthetic-v1",
                judge_type="mock",
                raw_judge_response="RAW_RESPONSE_MUST_NOT_BE_EXPORTED",
            )
        ],
        overall_score=0.7,
        overall_severity=SeverityLevel.MODERATE,
        summary="Synthetic rendering fixture. No independent assessment performed.",
        data_flow_disclosure="Offline fixture. No external model call.",
        scribeval_version="0.1.0",
        reproducibility=ReproducibilityMetadata(
            scribeval_version="0.1.0",
            judge_type="mock",
            judge_model="synthetic-model",
            judge_temperature=0.0,
            judge_seed=0,
            transcript_hash=content_hash("synthetic source"),
            scribe_note_hash=content_hash("synthetic note"),
            reference_note_hash=None,
            rubric_hashes={"omission": content_hash("synthetic rubric")},
            dimensions=["omission"],
        ),
        run_statistics=[
            DimensionRunStatistics(
                dimension="omission",
                run_count=3,
                mean_score=0.7,
                std_score=0.1,
                ci95_low=0.4,
                ci95_high=1.0,
                per_run_scores=[0.6, 0.7, 0.8],
            )
        ],
    )


class MarkdownGovernanceTests(unittest.TestCase):
    def test_use_limitations_precede_scores(self) -> None:
        report = synthetic_report()
        rendered = render_markdown(report)
        self.assertIn(report.notice, rendered)
        self.assertLess(rendered.index(report.notice), rendered.index("## Overall Score"))

    def test_provenance_preserves_zero_values_and_input_identity(self) -> None:
        report = synthetic_report()
        rendered = render_markdown(report)
        self.assertIn(report.reproducibility.transcript_hash, rendered)
        self.assertIn(report.reproducibility.scribe_note_hash, rendered)
        self.assertIn('"judge_temperature": 0.0', rendered)
        self.assertIn('"judge_seed": 0', rendered)
        self.assertIn('"reference_note_hash": null', rendered)

    def test_run_uncertainty_has_values_and_scope_limit(self) -> None:
        rendered = render_markdown(synthetic_report())
        self.assertIn("| omission | 3 | 0.7000 | 0.1000 | [0.4000, 1.0000] |", rendered)
        self.assertIn("do not estimate population-level clinical performance", rendered)

    def test_single_run_has_no_estimated_interval(self) -> None:
        report = synthetic_report()
        report.run_statistics = [
            DimensionRunStatistics(
                dimension="omission",
                run_count=1,
                mean_score=0.7,
                std_score=0.0,
                ci95_low=0.7,
                ci95_high=0.7,
                per_run_scores=[0.7],
            )
        ]
        rendered = render_markdown(report)
        self.assertIn(
            "| omission | 1 | 0.7000 | Not estimable | "
            "Not estimable (fewer than two runs) |",
            rendered,
        )
        self.assertNotIn("[0.7000, 0.7000]", rendered)

    def test_missing_metadata_is_explicit(self) -> None:
        report = synthetic_report().model_copy(
            update={"reproducibility": None, "run_statistics": []}
        )
        rendered = render_markdown(report)
        self.assertIn("input and configuration identity is unverified", rendered)
        self.assertIn("Repeated-run uncertainty was not recorded", rendered)

    def test_no_raw_response_leak_or_score_mutation_and_file_matches(self) -> None:
        report = synthetic_report()
        before = report.model_dump()
        with TemporaryDirectory() as directory:
            path = Path(directory) / "report.md"
            rendered = render_markdown(report, path)
            self.assertEqual(path.read_text(), rendered)
        self.assertNotIn("RAW_RESPONSE_MUST_NOT_BE_EXPORTED", rendered)
        self.assertEqual(before, report.model_dump())
        self.assertIn("Overall Score: 0.70", rendered)


if __name__ == "__main__":
    unittest.main()
