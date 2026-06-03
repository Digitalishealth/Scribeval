"""Scribeval CLI — evaluate final clinical notes against transcripts."""

from __future__ import annotations

import json
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from scribeval import __version__
from scribeval.benchmark import BenchmarkCase, BenchmarkReport, run_benchmark
from scribeval.clients.fhir import FHIRTerminologyClient
from scribeval.compare import MAX_SUBMISSIONS, BlindedReport, NoteSubmission
from scribeval.config import get_settings
from scribeval.evaluators import (
    DIMENSION_DESCRIPTIONS,
    EVALUATOR_REGISTRY,
    OPT_IN_DIMENSIONS,
)
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
from scribeval.profiling import ProfilingJudge
from scribeval.reporting.benchmark_report import (
    render_benchmark_json,
    render_benchmark_markdown,
)
from scribeval.reporting.comparison_report import (
    render_comparison_json,
    render_comparison_markdown,
)
from scribeval.reporting.json_report import render_json
from scribeval.reporting.markdown_report import render_markdown
from scribeval.rubrics.loader import load_rubric

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="scribeval")
def main() -> None:
    """Scribeval: Benchmark framework for transcript-to-note quality."""


@main.command()
@click.option(
    "--transcript",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Path to consultation transcript file.",
)
@click.option(
    "--candidate-note",
    "--scribe-note",
    "candidate_note",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Path to candidate final note file. --scribe-note is kept as an alias.",
)
@click.option(
    "--reference-note",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to optional adjudication reference note.",
)
@click.option(
    "--consultation-type",
    type=click.Choice([t.value for t in ConsultationType], case_sensitive=False),
    default="gp_standard",
    help="Type of consultation.",
)
@click.option(
    "--candidate-label",
    "--scribe-product",
    "candidate_label",
    default=None,
    help="Label for the candidate note, such as GP, ScribeA, or ScribeB.",
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
@click.option(
    "--runs",
    type=int,
    default=1,
    show_default=True,
    help="Number of times to evaluate each dimension. >1 reports variance.",
)
@click.option(
    "--seed",
    type=int,
    default=None,
    help="Seed to embed in the reproducibility metadata (for later replay).",
)
@click.option(
    "--profile/--no-profile",
    default=False,
    help="Wrap the judge with ProfilingJudge to record cost and latency.",
)
def evaluate(
    transcript: Path,
    candidate_note: Path,
    reference_note: Path | None,
    consultation_type: str,
    candidate_label: str | None,
    dimensions: str | None,
    output: Path | None,
    output_format: str,
    model: str | None,
    rubric_dir: Path | None,
    case_id: str | None,
    runs: int,
    seed: int | None,
    profile: bool,
) -> None:
    """Evaluate a final clinical note against the whole transcript."""
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
            content=candidate_note.read_text(),
            scribe_product=candidate_label,
        ),
        reference_note=(
            ReferenceNote(content=reference_note.read_text())
            if reference_note
            else None
        ),
    )

    # Build judge (temperature=0 by default for reproducibility)
    api_key = settings.anthropic_api_key or None
    judge_model = model or settings.default_model
    base_judge = LLMJudge(model=judge_model, api_key=api_key, seed=seed)
    # Optionally wrap with profiler for cost/latency reporting
    judge = ProfilingJudge(base_judge) if profile else base_judge

    # Build FHIR terminology client only if a dimension that needs it was requested.
    # Keeping construction conditional avoids surprising network dependencies for
    # users who only run the default dimensions. Fail-closed: if no endpoint is
    # configured, refuse to run the medication terminology dimension rather than
    # silently hitting a public default.
    fhir_client: FHIRTerminologyClient | None = None
    if "medication_terminology" in dim_list:
        if not settings.fhir_terminology_url:
            raise click.UsageError(
                "medication_terminology requires SCRIBEVAL_FHIR_TERMINOLOGY_URL "
                "to be set. Configure your own Ontoserver, or explicitly set "
                "it to the public CSIRO sandbox "
                "(https://r4.ontoserver.csiro.au/fhir) after reviewing the "
                "data-flow implications in DATA_FLOW.md."
            )
        fhir_client = FHIRTerminologyClient(
            endpoint=settings.fhir_terminology_url,
            timeout_seconds=settings.fhir_timeout_seconds,
        )

    # Show data flow before evaluation
    console.print("\n[bold]Data Flow Disclosure[/bold]")
    console.print(
        f"  Transcript and candidate note will be sent to {judge_model} via Anthropic API."
    )
    if reference_note:
        console.print("  Reference note will also be sent as optional adjudication context.")
    if fhir_client is not None:
        console.print(
            f"  Extracted medication names (no transcript, no PHI) will be "
            f"sent to FHIR terminology server: {fhir_client.endpoint}"
        )
    console.print()

    # Run evaluation
    if runs < 1:
        raise click.UsageError("--runs must be >= 1")
    console.print(
        f"[bold]Evaluating {len(dim_list)} dimension(s), "
        f"{runs} run(s) per dimension...[/bold]\n"
    )
    pipeline = EvaluationPipeline(
        dimensions=dim_list,
        judge=judge,
        rubric_dir=rubric_dir or settings.rubric_dir,
        fhir_client=fhir_client,
        runs=runs,
    )

    with console.status("Running evaluation..."):
        report = pipeline.evaluate_case(case)

    # Display results
    _display_results(report)

    if profile and isinstance(judge, ProfilingJudge):
        console.print(f"[bold]Profile:[/bold] {judge.report.format_summary()}")
        console.print()

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
    settings = get_settings()
    default_set = set(settings.default_dimensions)

    table = Table(title="Available Evaluation Dimensions")
    table.add_column("Dimension", style="bold")
    table.add_column("Default", justify="center")
    table.add_column("Description")

    for dim in sorted(EVALUATOR_REGISTRY.keys()):
        desc = DIMENSION_DESCRIPTIONS.get(dim, "")
        if dim in OPT_IN_DIMENSIONS:
            default_marker = "[yellow]opt-in[/yellow]"
        elif dim in default_set:
            default_marker = "[green]yes[/green]"
        else:
            default_marker = "no"
        table.add_row(dim, default_marker, desc)

    console.print(table)
    if OPT_IN_DIMENSIONS:
        console.print()
        console.print(
            "[dim]Opt-in dimensions are not enabled by default. Pass them "
            "explicitly via --dimensions, e.g. "
            "--dimensions omission,hallucination,medication_terminology[/dim]"
        )


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
@click.option(
    "--dimensions",
    default=None,
    help="Comma-separated list of dimensions to disclose (default: defaults).",
)
def show_data_flow(model: str | None, dimensions: str | None) -> None:
    """Show what data would be sent where during evaluation."""
    settings = get_settings()
    judge_model = model or settings.default_model
    dim_list = (
        [d.strip() for d in dimensions.split(",")]
        if dimensions
        else settings.default_dimensions
    )
    will_use_fhir = "medication_terminology" in dim_list

    console.print("[bold]Scribeval Data Flow Disclosure[/bold]\n")

    console.print("[bold]Service 1: Anthropic API (always used)[/bold]")
    console.print("[bold]What is sent to the Anthropic API:[/bold]")
    console.print("  1. The consultation transcript (full text)")
    console.print("  2. The candidate final note (full text)")
    console.print("  3. The reference note, if provided as adjudication context (full text)")
    console.print("  4. The evaluation rubric (scoring criteria)")
    console.print(f"  5. Model: {judge_model}")
    console.print()

    if will_use_fhir:
        console.print(
            "[bold]Service 2: FHIR Terminology Server "
            "(used by medication_terminology)[/bold]"
        )
        console.print(
            f"  Endpoint: {settings.fhir_terminology_url or '(not configured)'}"
        )
        console.print("[bold]What is sent to the FHIR server:[/bold]")
        console.print("  - Extracted medication name strings only (e.g. 'amoxicillin')")
        console.print("[bold]What is NOT sent to the FHIR server:[/bold]")
        console.print("  - The consultation transcript")
        console.print("  - The full candidate note")
        console.print("  - Patient identifiers or other clinical context")
        console.print(
            "  - There is NO default endpoint. Set "
            "SCRIBEVAL_FHIR_TERMINOLOGY_URL to a private Ontoserver, or "
            "explicitly to https://r4.ontoserver.csiro.au/fhir after "
            "reviewing data-flow implications."
        )
        console.print()
    else:
        console.print(
            "[dim]Service 2: FHIR Terminology Server — NOT used "
            "(medication_terminology not in selected dimensions).[/dim]\n"
        )

    console.print("[bold]What is NOT sent (any service):[/bold]")
    console.print("  - Patient identifiers (unless present in your input files)")
    console.print("  - Your API key is used for authentication only")
    console.print("  - No data is stored by Scribeval beyond local report files")
    console.print()

    console.print("[bold]Your responsibilities:[/bold]")
    console.print("  - De-identify clinical data BEFORE running evaluation")
    console.print("  - Ensure you have appropriate consent/authority to process the data")
    console.print("  - Review Anthropic's data retention policy")
    if will_use_fhir:
        console.print(
            "  - Review your FHIR terminology server's data handling policy"
        )
    console.print()

    console.print("[bold]Anthropic API data handling:[/bold]")
    console.print("  - See: https://www.anthropic.com/policies")
    console.print("  - API inputs are not used for model training by default")


# --------------------------------------------------------------------------- #
# Critique-defence commands
# --------------------------------------------------------------------------- #


@main.command("compare")
@click.option(
    "--transcript",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Shared consultation transcript all candidate notes summarise.",
)
@click.option(
    "--candidate-note",
    "--scribe-note",
    "candidate_notes",
    multiple=True,
    required=True,
    type=str,
    help="Candidate notes to compare, formatted as 'label=path'. Repeat flag "
    "for each submission; 2 to 5 submissions are supported. --scribe-note is "
    "kept as an alias.",
)
@click.option(
    "--reference-note",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Optional adjudication reference note. This is not scored as a submission.",
)
@click.option(
    "--consultation-type",
    type=click.Choice([t.value for t in ConsultationType], case_sensitive=False),
    default="gp_standard",
)
@click.option(
    "--dimensions",
    default=None,
    help="Comma-separated dimensions to evaluate.",
)
@click.option(
    "--rubric-dir",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Directory containing rubric YAML files.",
)
@click.option(
    "--runs",
    type=int,
    default=1,
    show_default=True,
    help="Number of times to evaluate each dimension. >1 reports variance.",
)
@click.option(
    "--seed",
    type=int,
    default=None,
    help="Seed for the blinded shuffle order.",
)
@click.option(
    "--model",
    default=None,
    help="Claude model to use.",
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=None,
    help="Output file path for the comparison report.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "markdown", "both"], case_sensitive=False),
    default=None,
    help="Optional comparison report output format.",
)
def compare_cmd(
    transcript: Path,
    candidate_notes: tuple[str, ...],
    reference_note: Path | None,
    consultation_type: str,
    dimensions: str | None,
    rubric_dir: Path | None,
    runs: int,
    seed: int | None,
    model: str | None,
    output: Path | None,
    output_format: str | None,
) -> None:
    """Blinded head-to-head comparison of multiple final notes.

    Each candidate note is labelled S1, S2, ... in a seed-shuffled order, and
    the original submission label is stripped before evaluation. The ranking is
    printed at the end.
    """
    from scribeval.compare import run_blinded_comparison

    settings = get_settings()
    submissions: list[NoteSubmission] = []
    for entry in candidate_notes:
        if "=" not in entry:
            raise click.UsageError(
                f"--candidate-note must be of the form 'label=path', got {entry!r}"
            )
        label, path_str = entry.split("=", 1)
        path = Path(path_str)
        if not path.exists():
            raise click.UsageError(f"Candidate note not found: {path}")
        submissions.append(
            NoteSubmission(
                label=label.strip(),
                note_content=path.read_text(),
            )
        )

    dim_list = (
        [d.strip() for d in dimensions.split(",")]
        if dimensions
        else settings.default_dimensions
    )

    fhir_client: FHIRTerminologyClient | None = None
    if "medication_terminology" in dim_list:
        if not settings.fhir_terminology_url:
            raise click.UsageError(
                "medication_terminology requires SCRIBEVAL_FHIR_TERMINOLOGY_URL "
                "to be set. Configure your own Ontoserver, or explicitly set "
                "it to the public CSIRO sandbox "
                "(https://r4.ontoserver.csiro.au/fhir) after reviewing the "
                "data-flow implications in DATA_FLOW.md."
            )
        fhir_client = FHIRTerminologyClient(
            endpoint=settings.fhir_terminology_url,
            timeout_seconds=settings.fhir_timeout_seconds,
        )

    if runs < 1:
        raise click.UsageError("--runs must be >= 1")

    judge = LLMJudge(
        model=model or settings.default_model,
        api_key=settings.anthropic_api_key or None,
    )
    pipeline = EvaluationPipeline(
        dimensions=dim_list,
        judge=judge,
        rubric_dir=rubric_dir or settings.rubric_dir,
        fhir_client=fhir_client,
        runs=runs,
    )

    reference_content = reference_note.read_text() if reference_note else None

    try:
        result = run_blinded_comparison(
            transcript_content=transcript.read_text(),
            submissions=submissions,
            pipeline=pipeline,
            consultation_type=ConsultationType(consultation_type),
            reference_note_content=reference_content,
            rng_seed=seed,
        )
    except ValueError as exc:
        raise click.UsageError(str(exc)) from exc

    table = Table(title="Blinded Transcript-to-Note Comparison")
    table.add_column("Rank", justify="right")
    table.add_column("Blinded Label", style="bold")
    table.add_column("Submission (revealed)")
    table.add_column("Overall Score", justify="right")
    for rank, (label, score) in enumerate(result.ranking, start=1):
        table.add_row(
            str(rank),
            label,
            result.label_to_submission[label],
            f"{score:.3f}",
        )
    console.print(table)

    if output or output_format:
        _write_comparison_output(result, output, output_format or "both")


def _write_comparison_output(
    report: BlindedReport,
    output: Path | None,
    output_format: str,
) -> None:
    """Write comparison report to file(s)."""
    base = output.stem if output else report.comparison_id
    parent = output.parent if output else Path(".")

    if output_format in ("json", "both"):
        json_path = parent / f"{base}.json"
        render_comparison_json(report, json_path)
        console.print(f"JSON comparison report written to: {json_path}")

    if output_format in ("markdown", "both"):
        md_path = parent / f"{base}.md"
        render_comparison_markdown(report, md_path)
        console.print(f"Markdown comparison report written to: {md_path}")


@main.command("benchmark")
@click.argument("manifest", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--dimensions",
    default=None,
    help="Comma-separated dimensions to evaluate.",
)
@click.option(
    "--rubric-dir",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Directory containing rubric YAML files.",
)
@click.option(
    "--runs",
    type=int,
    default=1,
    show_default=True,
    help="Number of times to evaluate each dimension. >1 reports variance.",
)
@click.option(
    "--seed",
    type=int,
    default=None,
    help="Seed for deterministic blinded shuffle order per case.",
)
@click.option(
    "--model",
    default=None,
    help="Claude model to use.",
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=None,
    help="Output file path for the benchmark report.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "markdown", "both"], case_sensitive=False),
    default=None,
    help="Optional benchmark report output format.",
)
def benchmark_cmd(
    manifest: Path,
    dimensions: str | None,
    rubric_dir: Path | None,
    runs: int,
    seed: int | None,
    model: str | None,
    output: Path | None,
    output_format: str | None,
) -> None:
    """Run a multi-case benchmark from a JSON manifest."""
    settings = get_settings()
    dim_list = (
        [d.strip() for d in dimensions.split(",")]
        if dimensions
        else settings.default_dimensions
    )

    fhir_client: FHIRTerminologyClient | None = None
    if "medication_terminology" in dim_list:
        if not settings.fhir_terminology_url:
            raise click.UsageError(
                "medication_terminology requires SCRIBEVAL_FHIR_TERMINOLOGY_URL "
                "to be set. Configure your own Ontoserver, or explicitly set "
                "it to the public CSIRO sandbox "
                "(https://r4.ontoserver.csiro.au/fhir) after reviewing the "
                "data-flow implications in DATA_FLOW.md."
            )
        fhir_client = FHIRTerminologyClient(
            endpoint=settings.fhir_terminology_url,
            timeout_seconds=settings.fhir_timeout_seconds,
        )

    if runs < 1:
        raise click.UsageError("--runs must be >= 1")

    cases = _load_benchmark_manifest(manifest)
    judge = LLMJudge(
        model=model or settings.default_model,
        api_key=settings.anthropic_api_key or None,
    )
    pipeline = EvaluationPipeline(
        dimensions=dim_list,
        judge=judge,
        rubric_dir=rubric_dir or settings.rubric_dir,
        fhir_client=fhir_client,
        runs=runs,
    )

    try:
        result = run_benchmark(cases=cases, pipeline=pipeline, rng_seed=seed)
    except ValueError as exc:
        raise click.UsageError(str(exc)) from exc

    table = Table(title="Scribeval Multi-Case Benchmark")
    table.add_column("Rank", justify="right")
    table.add_column("Submission", style="bold")
    table.add_column("Mean Score", justify="right")
    table.add_column("Score SD", justify="right")
    table.add_column("Critical Findings", justify="right")
    for rank, (label, mean_score) in enumerate(result.ranking, start=1):
        summary = result.submission_summaries[label]
        table.add_row(
            str(rank),
            label,
            f"{mean_score:.3f}",
            f"{summary.std_overall_score:.3f}",
            str(summary.critical_finding_count),
        )
    console.print(table)

    if output or output_format:
        _write_benchmark_output(result, output, output_format or "both")


def _load_benchmark_manifest(manifest: Path) -> list[BenchmarkCase]:
    """Load benchmark cases from a JSON manifest."""
    try:
        data = json.loads(manifest.read_text())
    except json.JSONDecodeError as exc:
        raise click.UsageError(f"Invalid benchmark manifest JSON: {exc}") from exc

    raw_cases = data.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise click.UsageError("Benchmark manifest must contain a non-empty 'cases' list.")

    cases: list[BenchmarkCase] = []
    for idx, raw_case in enumerate(raw_cases, start=1):
        if not isinstance(raw_case, dict):
            raise click.UsageError(f"Case {idx} must be an object.")

        case_id = str(raw_case.get("case_id") or f"case_{idx}")
        transcript_path = _manifest_path(manifest, raw_case.get("transcript"), case_id)
        reference_note = raw_case.get("reference_note")
        reference_content = None
        if reference_note:
            reference_content = _manifest_path(
                manifest,
                reference_note,
                case_id,
            ).read_text()

        raw_candidates = raw_case.get("candidate_notes")
        if not isinstance(raw_candidates, dict):
            raise click.UsageError(
                f"Case {case_id!r} must define candidate_notes as a label-to-path object."
            )

        submissions: list[NoteSubmission] = []
        for label, path in raw_candidates.items():
            label_text = str(label).strip()
            if not label_text:
                raise click.UsageError(
                    f"Case {case_id!r} contains an empty candidate label."
                )
            submissions.append(
                NoteSubmission(
                    label=label_text,
                    note_content=_manifest_path(manifest, path, case_id).read_text(),
                )
            )
        if len(submissions) < 2:
            raise click.UsageError(
                f"Case {case_id!r} must include at least two candidate notes."
            )
        if len(submissions) > MAX_SUBMISSIONS:
            raise click.UsageError(
                f"Case {case_id!r} must include at most {MAX_SUBMISSIONS} "
                "candidate notes."
            )

        try:
            consultation_type = ConsultationType(
                raw_case.get("consultation_type", ConsultationType.GP_STANDARD.value)
            )
        except ValueError as exc:
            available = ", ".join(t.value for t in ConsultationType)
            raise click.UsageError(
                f"Case {case_id!r} has invalid consultation_type. "
                f"Available: {available}."
            ) from exc
        cases.append(
            BenchmarkCase(
                case_id=case_id,
                transcript_content=transcript_path.read_text(),
                submissions=submissions,
                consultation_type=consultation_type,
                reference_note_content=reference_content,
            )
        )

    return cases


def _manifest_path(manifest: Path, value: object, case_id: str) -> Path:
    """Resolve a manifest path value relative to the manifest file."""
    if not isinstance(value, str) or not value:
        raise click.UsageError(f"Case {case_id!r} has an invalid path value.")
    path = Path(value)
    if not path.is_absolute():
        path = manifest.parent / path
    if not path.exists():
        raise click.UsageError(f"Manifest path not found for case {case_id!r}: {path}")
    return path


def _write_benchmark_output(
    report: BenchmarkReport,
    output: Path | None,
    output_format: str,
) -> None:
    """Write benchmark report to file(s)."""
    base = output.stem if output else report.benchmark_id
    parent = output.parent if output else Path(".")

    if output_format in ("json", "both"):
        json_path = parent / f"{base}.json"
        render_benchmark_json(report, json_path)
        console.print(f"JSON benchmark report written to: {json_path}")

    if output_format in ("markdown", "both"):
        md_path = parent / f"{base}.md"
        render_benchmark_markdown(report, md_path)
        console.print(f"Markdown benchmark report written to: {md_path}")


@main.command("verify-detection")
@click.option(
    "--scribe-note",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Clean scribe note into which errors will be injected.",
)
@click.option(
    "--transcript",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Consultation transcript (unchanged).",
)
@click.option(
    "--consultation-type",
    type=click.Choice([t.value for t in ConsultationType], case_sensitive=False),
    default="gp_standard",
)
@click.option(
    "--seed",
    type=int,
    default=None,
    help="Seed controlling which errors are injected.",
)
@click.option(
    "--model",
    default=None,
    help="Claude model to use.",
)
def verify_detection(
    scribe_note: Path,
    transcript: Path,
    consultation_type: str,
    seed: int | None,
    model: str | None,
) -> None:
    """Inject deterministic errors into a clean note and measure recall."""
    from scribeval.error_injection import inject_errors, score_detection

    settings = get_settings()
    corrupted = inject_errors(scribe_note.read_text(), seed=seed)
    console.print(
        f"[bold]Injected {len(corrupted.injected_errors)} errors[/bold] into "
        f"the scribe note (seed={seed})"
    )
    for err in corrupted.injected_errors:
        console.print(f"  - [{err.error_type.value}] {err.description}")

    case = EvaluationCase(
        case_id=scribe_note.stem + "_injected",
        consultation_type=ConsultationType(consultation_type),
        transcript=Transcript(content=transcript.read_text()),
        scribe_note=ScribeNote(content=corrupted.corrupted),
    )

    judge = LLMJudge(
        model=model or settings.default_model,
        api_key=settings.anthropic_api_key or None,
    )
    pipeline = EvaluationPipeline(
        dimensions=["omission", "hallucination"],
        judge=judge,
        rubric_dir=settings.rubric_dir,
    )
    report = pipeline.evaluate_case(case)

    # Flatten all findings across dimensions for detection scoring. The
    # detection scorer takes plain dicts so it does not couple to the
    # evaluation report schema.
    all_findings = [
        {
            "description": f.description,
            "note_excerpt": f.note_excerpt or "",
        }
        for ds in report.dimension_scores
        for f in ds.findings
    ]
    detection = score_detection(corrupted.injected_errors, all_findings)

    console.print(
        f"\n[bold]Detection recall: "
        f"{detection.recall:.2%}[/bold] "
        f"({detection.detected_count}/{detection.total_injected})"
    )
    for err in corrupted.injected_errors:
        detected = detection.per_type_detection.get(err.error_type.value, False)
        mark = "[green]\u2713[/green]" if detected else "[red]\u2717[/red]"
        console.print(f"  {mark} [{err.error_type.value}] {err.description}")
    if detection.false_positive_count:
        console.print(
            f"[yellow]{detection.false_positive_count} finding(s) were not "
            "matched to any injected error (possible real issues or "
            "false positives).[/yellow]"
        )


@main.command("calibrate")
@click.argument("pairs_json", type=click.Path(exists=True, path_type=Path))
def calibrate_cmd(pairs_json: Path) -> None:
    """Compute inter-rater agreement from a JSON file of rating pairs.

    The input file should be a list of objects with fields: dimension,
    judge_score, human_score, judge_severity, human_severity.
    """
    import json

    from scribeval.calibration import RatingPair, compute_agreement

    raw = json.loads(pairs_json.read_text())
    pairs = [
        RatingPair(
            dimension=r["dimension"],
            judge_score=float(r["judge_score"]),
            human_score=float(r["human_score"]),
            judge_severity=str(r["judge_severity"]),
            human_severity=str(r["human_severity"]),
        )
        for r in raw
    ]
    agreements = compute_agreement(pairs)

    table = Table(title="Inter-rater agreement (judge vs human)")
    table.add_column("Dimension", style="bold")
    table.add_column("N", justify="right")
    table.add_column("Weighted \u03ba", justify="right")
    table.add_column("\u03ba interpretation")
    table.add_column("ICC(2,1)", justify="right")
    table.add_column("Mean |diff|", justify="right")
    for a in agreements:
        table.add_row(
            a.dimension,
            str(a.n_pairs),
            f"{a.kappa:.3f}",
            a.interpret_kappa(),
            f"{a.icc:.3f}",
            f"{a.mean_abs_difference:.3f}",
        )
    console.print(table)


@main.command("sensitivity")
@click.argument("report_json", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--perturbation",
    type=float,
    default=0.20,
    show_default=True,
    help="Fractional weight perturbation to explore (0.2 = +/-20%).",
)
def sensitivity_cmd(report_json: Path, perturbation: float) -> None:
    """Run cheap weight-sensitivity analysis on a completed report."""
    import json

    from scribeval.sensitivity import sensitivity_analysis

    data = json.loads(report_json.read_text())
    report = EvaluationReport.model_validate(data)
    result = sensitivity_analysis(report, perturbation=perturbation)

    console.print(f"[bold]Baseline overall score:[/bold] {result.baseline_score:.3f}")
    console.print(f"[bold]Score range under perturbation:[/bold] "
                  f"{result.min_score:.3f} \u2013 {result.max_score:.3f} "
                  f"(range {result.score_range:.3f})")
    if result.robust:
        console.print("[green]Result is robust to plausible weight changes "
                      "(range <= 0.10).[/green]")
    else:
        console.print("[yellow]Result is sensitive to weight changes "
                      "(range > 0.10). Report the range alongside the "
                      "point estimate.[/yellow]")
    table = Table(title="Sensitivity scenarios")
    table.add_column("Scenario", style="bold")
    table.add_column("Overall Score", justify="right")
    for scenario in result.scenarios:
        table.add_row(scenario["name"], f"{scenario['overall_score']:.3f}")
    console.print(table)
