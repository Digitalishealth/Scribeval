"""Scribeval CLI — evaluate AI medical scribe outputs."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from scribeval import __version__
from scribeval.config import get_settings
from scribeval.evaluators import DIMENSION_DESCRIPTIONS, EVALUATOR_REGISTRY
from scribeval.judges.llm import LLMJudge
from scribeval.models.case import (
    ConsultationType,
    EvaluationCase,
    ReferenceNote,
    ScribeNote,
    Transcript,
)
from scribeval.models.report import EvaluationReport
from scribeval.models.score import SeverityLevel
from scribeval.pipeline import EvaluationPipeline
from scribeval.reporting.json_report import render_json
from scribeval.reporting.markdown_report import render_markdown
from scribeval.rubrics.loader import load_rubric

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="scribeval")
def main() -> None:
    """Scribeval: Evaluation framework for AI medical scribes."""


@main.command()
@click.option(
    "--transcript",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Path to consultation transcript file.",
)
@click.option(
    "--scribe-note",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Path to AI scribe output note file.",
)
@click.option(
    "--reference-note",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to gold-standard reference note (optional).",
)
@click.option(
    "--consultation-type",
    type=click.Choice([t.value for t in ConsultationType], case_sensitive=False),
    default="gp_standard",
    help="Type of consultation.",
)
@click.option(
    "--scribe-product",
    default=None,
    help="Name of the AI scribe product being evaluated.",
)
@click.option(
    "--dimensions",
    default=None,
    help="Comma-separated list of dimensions to evaluate (default: all).",
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=None,
    help="Output file path for the report.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "markdown", "both"], case_sensitive=False),
    default="both",
    help="Output format.",
)
@click.option(
    "--model",
    default=None,
    help="Claude model to use for evaluation (default: from config).",
)
@click.option(
    "--rubric-dir",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Directory containing rubric YAML files.",
)
@click.option(
    "--case-id",
    default=None,
    help="Identifier for this evaluation case.",
)
def evaluate(
    transcript: Path,
    scribe_note: Path,
    reference_note: Path | None,
    consultation_type: str,
    scribe_product: str | None,
    dimensions: str | None,
    output: Path | None,
    output_format: str,
    model: str | None,
    rubric_dir: Path | None,
    case_id: str | None,
) -> None:
    """Evaluate an AI scribe's output against clinical safety dimensions."""
    settings = get_settings()

    # Parse dimensions
    dim_list = (
        [d.strip() for d in dimensions.split(",")]
        if dimensions
        else settings.default_dimensions
    )

    # Build case
    case = EvaluationCase(
        case_id=case_id or transcript.stem,
        consultation_type=ConsultationType(consultation_type),
        transcript=Transcript(content=transcript.read_text()),
        scribe_note=ScribeNote(
            content=scribe_note.read_text(),
            scribe_product=scribe_product,
        ),
        reference_note=(
            ReferenceNote(content=reference_note.read_text())
            if reference_note
            else None
        ),
    )

    # Build judge
    api_key = settings.anthropic_api_key or None
    judge_model = model or settings.default_model
    judge = LLMJudge(model=judge_model, api_key=api_key)

    # Show data flow before evaluation
    console.print("\n[bold]Data Flow Disclosure[/bold]")
    console.print(
        f"  Transcript and scribe note will be sent to {judge_model} via Anthropic API."
    )
    if reference_note:
        console.print("  Reference note will also be sent for comparison.")
    console.print()

    # Run evaluation
    console.print(f"[bold]Evaluating {len(dim_list)} dimension(s)...[/bold]\n")
    pipeline = EvaluationPipeline(
        dimensions=dim_list,
        judge=judge,
        rubric_dir=rubric_dir or settings.rubric_dir,
    )

    with console.status("Running evaluation..."):
        report = pipeline.evaluate_case(case)

    # Display results
    _display_results(report)

    # Write output
    if output or output_format:
        _write_output(report, output, output_format)


def _display_results(report: EvaluationReport) -> None:
    """Display evaluation results in the terminal."""
    severity_colors = {
        SeverityLevel.NONE: "green",
        SeverityLevel.LOW: "blue",
        SeverityLevel.MODERATE: "yellow",
        SeverityLevel.HIGH: "red",
        SeverityLevel.CRITICAL: "bold red",
    }

    console.print(f"\n[bold]Overall Score: {report.overall_score:.2f}/1.00[/bold]")
    color = severity_colors.get(report.overall_severity, "white")
    console.print(f"[{color}]Severity: {report.overall_severity.value.upper()}[/{color}]\n")

    table = Table(title="Dimension Scores")
    table.add_column("Dimension", style="bold")
    table.add_column("Score", justify="right")
    table.add_column("Severity")
    table.add_column("Findings", justify="right")

    for ds in report.dimension_scores:
        sev_color = severity_colors.get(ds.severity_summary, "white")
        table.add_row(
            ds.dimension.replace("_", " ").title(),
            f"{ds.score:.2f}",
            f"[{sev_color}]{ds.severity_summary.value}[/{sev_color}]",
            str(len(ds.findings)),
        )

    console.print(table)
    console.print()

    # Show critical findings
    critical = [
        (ds.dimension, f)
        for ds in report.dimension_scores
        for f in ds.findings
        if f.severity == SeverityLevel.CRITICAL
    ]
    if critical:
        console.print(f"[bold red]Critical Findings ({len(critical)}):[/bold red]")
        for dim, finding in critical:
            console.print(f"  [{dim}] {finding.description}")
        console.print()


def _write_output(
    report: EvaluationReport,
    output: Path | None,
    output_format: str,
) -> None:
    """Write report to file(s)."""
    base = output.stem if output else report.case_id
    parent = output.parent if output else Path(".")

    if output_format in ("json", "both"):
        json_path = parent / f"{base}.json"
        render_json(report, json_path)
        console.print(f"JSON report written to: {json_path}")

    if output_format in ("markdown", "both"):
        md_path = parent / f"{base}.md"
        render_markdown(report, md_path)
        console.print(f"Markdown report written to: {md_path}")


@main.command("list-dimensions")
def list_dimensions() -> None:
    """List all available evaluation dimensions."""
    table = Table(title="Available Evaluation Dimensions")
    table.add_column("Dimension", style="bold")
    table.add_column("Description")

    for dim in sorted(EVALUATOR_REGISTRY.keys()):
        desc = DIMENSION_DESCRIPTIONS.get(dim, "")
        table.add_row(dim, desc)

    console.print(table)


@main.command("validate-rubric")
@click.argument("rubric_path", type=click.Path(exists=True, path_type=Path))
def validate_rubric(rubric_path: Path) -> None:
    """Validate a rubric YAML file against the schema."""
    try:
        rubric = load_rubric(rubric_path)
        console.print(f"[green]Valid:[/green] {rubric.display_name} v{rubric.version}")
        console.print(f"  Dimension: {rubric.dimension}")
        console.print(f"  Severity levels: {', '.join(rubric.severity_criteria.keys())}")
        console.print(f"  References: {len(rubric.references)}")
    except Exception as e:
        console.print(f"[red]Invalid:[/red] {e}")
        raise SystemExit(1) from e


@main.command("show-data-flow")
@click.option("--model", default=None, help="Model that would be used.")
def show_data_flow(model: str | None) -> None:
    """Show what data would be sent where during evaluation."""
    settings = get_settings()
    judge_model = model or settings.default_model

    console.print("[bold]Scribeval Data Flow Disclosure[/bold]\n")

    console.print("[bold]What is sent to the Anthropic API:[/bold]")
    console.print("  1. The consultation transcript (full text)")
    console.print("  2. The AI scribe output note (full text)")
    console.print("  3. The reference note, if provided (full text)")
    console.print("  4. The evaluation rubric (scoring criteria)")
    console.print(f"  5. Model: {judge_model}")
    console.print()

    console.print("[bold]What is NOT sent:[/bold]")
    console.print("  - Patient identifiers (unless present in your input files)")
    console.print("  - Your API key is used for authentication only")
    console.print("  - No data is stored by Scribeval beyond local report files")
    console.print()

    console.print("[bold]Your responsibilities:[/bold]")
    console.print("  - De-identify clinical data BEFORE running evaluation")
    console.print("  - Ensure you have appropriate consent/authority to process the data")
    console.print("  - Review Anthropic's data retention policy")
    console.print()

    console.print("[bold]Anthropic API data handling:[/bold]")
    console.print("  - See: https://www.anthropic.com/policies")
    console.print("  - API inputs are not used for model training by default")
