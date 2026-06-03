"""Tests for the CLI interface."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from scribeval.cli import main
from tests.conftest import MockJudge


class CLIMockJudge(MockJudge):
    """Mock judge accepting the same constructor shape as LLMJudge."""

    def __init__(self, *args, **kwargs):
        super().__init__()


def _write_case_files(tmp_path: Path) -> tuple[Path, Path, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    transcript = tmp_path / "transcript.txt"
    ai_note = tmp_path / "ai_note.txt"
    gp_note = tmp_path / "gp_note.txt"
    transcript.write_text("Patient reports cough for three days. No fever.")
    ai_note.write_text("Cough for three days. Afebrile.")
    gp_note.write_text("Three day cough without fever.")
    return transcript, ai_note, gp_note


def _write_benchmark_manifest(tmp_path: Path) -> Path:
    transcript_a, ai_note_a, gp_note_a = _write_case_files(tmp_path / "case_a")
    transcript_b, ai_note_b, gp_note_b = _write_case_files(tmp_path / "case_b")
    manifest = tmp_path / "benchmark.json"
    manifest.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "case_id": "case_a",
                        "transcript": str(transcript_a),
                        "candidate_notes": {
                            "GP": str(gp_note_a),
                            "AI": str(ai_note_a),
                        },
                    },
                    {
                        "case_id": "case_b",
                        "transcript": str(transcript_b),
                        "candidate_notes": {
                            "GP": str(gp_note_b),
                            "AI": str(ai_note_b),
                        },
                    },
                ]
            }
        )
    )
    return manifest


class TestCLI:
    def test_version(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_list_dimensions(self):
        runner = CliRunner()
        result = runner.invoke(main, ["list-dimensions"])
        assert result.exit_code == 0
        assert "omission" in result.output.lower()
        assert "hallucination" in result.output.lower()
        assert "medicolegal" in result.output.lower()
        assert "ahpra" in result.output.lower()

    def test_validate_rubric(self, rubrics_dir):
        runner = CliRunner()
        result = runner.invoke(
            main, ["validate-rubric", str(rubrics_dir / "omission.yaml")]
        )
        assert result.exit_code == 0
        assert "Valid" in result.output

    def test_validate_all_rubrics(self, rubrics_dir):
        runner = CliRunner()
        for rubric_file in rubrics_dir.glob("*.yaml"):
            result = runner.invoke(main, ["validate-rubric", str(rubric_file)])
            assert result.exit_code == 0, f"Failed for {rubric_file.name}: {result.output}"

    def test_show_data_flow(self):
        runner = CliRunner()
        result = runner.invoke(main, ["show-data-flow"])
        assert result.exit_code == 0
        assert "Anthropic API" in result.output
        assert "De-identify" in result.output

    def test_evaluate_missing_files(self):
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "evaluate",
                "--transcript",
                "nonexistent.txt",
                "--scribe-note",
                "nonexistent.txt",
            ],
        )
        assert result.exit_code != 0

    def test_evaluate_accepts_candidate_note_alias(self, tmp_path, monkeypatch):
        monkeypatch.setattr("scribeval.cli.LLMJudge", CLIMockJudge)
        transcript, ai_note, _ = _write_case_files(tmp_path)
        output = tmp_path / "candidate_report"

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "evaluate",
                "--transcript",
                str(transcript),
                "--candidate-note",
                str(ai_note),
                "--candidate-label",
                "Heidi",
                "--dimensions",
                "omission",
                "--format",
                "json",
                "--output",
                str(output),
            ],
        )

        assert result.exit_code == 0, result.output
        report_json = output.with_suffix(".json").read_text()
        assert '"candidate_label": "Heidi"' in report_json

    def test_evaluate_keeps_scribe_note_alias(self, tmp_path, monkeypatch):
        monkeypatch.setattr("scribeval.cli.LLMJudge", CLIMockJudge)
        transcript, ai_note, _ = _write_case_files(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "evaluate",
                "--transcript",
                str(transcript),
                "--scribe-note",
                str(ai_note),
                "--scribe-product",
                "LegacyScribe",
                "--dimensions",
                "omission",
                "--format",
                "json",
                "--output",
                str(tmp_path / "legacy_report"),
            ],
        )

        assert result.exit_code == 0, result.output

    def test_compare_accepts_gp_and_ai_candidate_notes(self, tmp_path, monkeypatch):
        monkeypatch.setattr("scribeval.cli.LLMJudge", CLIMockJudge)
        transcript, ai_note, gp_note = _write_case_files(tmp_path)
        output = tmp_path / "comparison"

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "compare",
                "--transcript",
                str(transcript),
                "--candidate-note",
                f"GP={gp_note}",
                "--candidate-note",
                f"AI={ai_note}",
                "--dimensions",
                "omission",
                "--seed",
                "1",
                "--output",
                str(output),
                "--format",
                "both",
            ],
        )

        assert result.exit_code == 0, result.output
        assert "Blinded Transcript-to-Note Comparison" in result.output
        assert "Submission (revealed)" in result.output
        assert "GP" in result.output
        assert "AI" in result.output
        assert output.with_suffix(".json").exists()
        assert output.with_suffix(".md").exists()
        assert '"label_to_submission"' in output.with_suffix(".json").read_text()
        assert "Scribeval Comparison Report" in output.with_suffix(".md").read_text()

    def test_compare_keeps_scribe_note_alias(self, tmp_path, monkeypatch):
        monkeypatch.setattr("scribeval.cli.LLMJudge", CLIMockJudge)
        transcript, ai_note, gp_note = _write_case_files(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "compare",
                "--transcript",
                str(transcript),
                "--scribe-note",
                f"heidi={ai_note}",
                "--scribe-note",
                f"gp={gp_note}",
                "--dimensions",
                "omission",
            ],
        )

        assert result.exit_code == 0, result.output

    def test_compare_rejects_invalid_runs(self, tmp_path, monkeypatch):
        monkeypatch.setattr("scribeval.cli.LLMJudge", CLIMockJudge)
        transcript, ai_note, gp_note = _write_case_files(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "compare",
                "--transcript",
                str(transcript),
                "--candidate-note",
                f"GP={gp_note}",
                "--candidate-note",
                f"AI={ai_note}",
                "--dimensions",
                "omission",
                "--runs",
                "0",
            ],
        )

        assert result.exit_code != 0
        assert "--runs must be >= 1" in result.output

    def test_compare_medication_terminology_requires_fhir_url(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setattr("scribeval.cli.LLMJudge", CLIMockJudge)
        monkeypatch.delenv("SCRIBEVAL_FHIR_TERMINOLOGY_URL", raising=False)
        transcript, ai_note, gp_note = _write_case_files(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "compare",
                "--transcript",
                str(transcript),
                "--candidate-note",
                f"GP={gp_note}",
                "--candidate-note",
                f"AI={ai_note}",
                "--dimensions",
                "medication_terminology",
            ],
        )

        assert result.exit_code != 0
        assert "medication_terminology requires SCRIBEVAL_FHIR_TERMINOLOGY_URL" in (
            result.output
        )

    def test_benchmark_runs_manifest_and_writes_reports(self, tmp_path, monkeypatch):
        monkeypatch.setattr("scribeval.cli.LLMJudge", CLIMockJudge)
        manifest = _write_benchmark_manifest(tmp_path)
        output = tmp_path / "benchmark_report"

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "benchmark",
                str(manifest),
                "--dimensions",
                "omission",
                "--seed",
                "3",
                "--output",
                str(output),
                "--format",
                "both",
            ],
        )

        assert result.exit_code == 0, result.output
        assert "Scribeval Multi-Case Benchmark" in result.output
        assert "Mean Score" in result.output
        assert output.with_suffix(".json").exists()
        assert output.with_suffix(".md").exists()
        benchmark_json = output.with_suffix(".json").read_text()
        benchmark_md = output.with_suffix(".md").read_text()
        assert '"case_count": 2' in benchmark_json
        assert '"submission_summaries"' in benchmark_json
        assert "Scribeval Benchmark Report" in benchmark_md

    def test_benchmark_requires_consistent_submission_labels(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setattr("scribeval.cli.LLMJudge", CLIMockJudge)
        transcript_a, ai_note_a, gp_note_a = _write_case_files(tmp_path / "case_a")
        transcript_b, ai_note_b, gp_note_b = _write_case_files(tmp_path / "case_b")
        manifest = tmp_path / "benchmark_bad.json"
        manifest.write_text(
            json.dumps(
                {
                    "cases": [
                        {
                            "case_id": "case_a",
                            "transcript": str(transcript_a),
                            "candidate_notes": {
                                "GP": str(gp_note_a),
                                "AI": str(ai_note_a),
                            },
                        },
                        {
                            "case_id": "case_b",
                            "transcript": str(transcript_b),
                            "candidate_notes": {
                                "GP": str(gp_note_b),
                                "OtherAI": str(ai_note_b),
                            },
                        },
                    ]
                }
            )
        )

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "benchmark",
                str(manifest),
                "--dimensions",
                "omission",
            ],
        )

        assert result.exit_code != 0
        assert "same submission labels" in result.output

    def test_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Scribeval" in result.output

    def test_evaluate_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["evaluate", "--help"])
        assert result.exit_code == 0
        assert "--transcript" in result.output
        assert "--candidate-note" in result.output
        assert "--scribe-note" in result.output
        assert "--reference-note" in result.output
