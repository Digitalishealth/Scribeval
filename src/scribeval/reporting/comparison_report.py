"""Render blinded comparison reports for product-choice workflows."""

from __future__ import annotations

from pathlib import Path

from scribeval.compare import BlindedReport
from scribeval.models.score import SeverityLevel

SEVERITY_LABELS = {
    SeverityLevel.NONE: "None",
    SeverityLevel.LOW: "Low",
    SeverityLevel.MODERATE: "Moderate",
    SeverityLevel.HIGH: "High",
    SeverityLevel.CRITICAL: "CRITICAL",
}


def render_comparison_json(
    report: BlindedReport,
    output_path: Path | None = None,
) -> str:
    """Render a blinded comparison report as formatted JSON."""
    json_str = report.model_dump_json(indent=2)
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json_str)
    return json_str


def render_comparison_markdown(
    report: BlindedReport,
    output_path: Path | None = None,
) -> str:
    """Render a blinded comparison report as Markdown."""
    lines: list[str] = [
        "# Scribeval Comparison Report",
        "",
        f"**Comparison ID:** {report.comparison_id}",
        f"**Transcript Hash:** `{report.transcript_hash}`",
        f"**Generated:** {report.timestamp.isoformat()}",
        "",
        "## Ranking",
        "",
        "| Rank | Blinded Label | Submission | Overall Score | Severity |",
        "|------|---------------|------------|---------------|----------|",
    ]

    for rank, (label, score) in enumerate(report.ranking, start=1):
        single_report = report.per_label_reports[label]
        severity = SEVERITY_LABELS.get(
            single_report.overall_severity,
            single_report.overall_severity.value,
        )
        lines.append(
            f"| {rank} | {label} | {report.label_to_submission[label]} | "
            f"{score:.3f} | {severity} |"
        )

    lines.extend(["", "## Dimension Scores", ""])

    for label, _score in report.ranking:
        single_report = report.per_label_reports[label]
        lines.extend(
            [
                f"### {label}: {report.label_to_submission[label]}",
                "",
                "| Dimension | Score | Severity | Findings |",
                "|-----------|-------|----------|----------|",
            ]
        )
        for dimension_score in single_report.dimension_scores:
            severity = SEVERITY_LABELS.get(
                dimension_score.severity_summary,
                dimension_score.severity_summary.value,
            )
            dimension = dimension_score.dimension.replace("_", " ").title()
            lines.append(
                f"| {dimension} | {dimension_score.score:.2f} | {severity} | "
                f"{len(dimension_score.findings)} |"
            )
        lines.append("")

    lines.extend(
        [
            "## Notes",
            "",
            "- Submissions are blinded during scoring; original labels are revealed only "
            "in this report.",
            "- GP-written notes and AI-generated notes are scored through the same "
            "transcript-to-note pipeline.",
            "- Reference notes, when supplied, are optional adjudication context and are "
            "not scored as submissions.",
            "",
        ]
    )

    markdown = "\n".join(lines)
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown)
    return markdown
