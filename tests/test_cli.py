"""Tests for the CLI interface."""

from __future__ import annotations

from click.testing import CliRunner

from scribeval.cli import main


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
        assert "--scribe-note" in result.output
        assert "--reference-note" in result.output
