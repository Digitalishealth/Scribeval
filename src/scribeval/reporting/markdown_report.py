"""Markdown report renderer for human-readable evaluation reports."""

from __future__ import annotations

from pathlib import Path

from scribeval.models.report import EvaluationReport
from scribeval.models.score import DimensionScore, SeverityLevel

SEVERITY_LABELS = {
    SeverityLevel.NONE: "None",
    SeverityLevel.LOW: "Low",
    SeverityLevel.MODERATE: "Moderate",
    SeverityLevel.HIGH: "High",
    SeverityLevel.CRITICAL: "CRITICAL",
}


def _score_bar(score: float, width: int = 20) -> str:
    """Create a text-based score bar."""
    filled = round(score * width)
    return "[" + "#" * filled + "-" * (width - filled) + "]"


def _render_dimension(ds: DimensionScore) -> str:
    """Render a single dimension's detailed findings."""
    lines = []
    severity_label = SEVERITY_LABELS.get(ds.severity_summary, ds.severity_summary.value)
    dim_title = ds.dimension.replace("_", " ").title()
    lines.append(f"### {dim_title} ({ds.score:.2f} - {severity_label})")
    lines.append("")

    if ds.reasoning:
        lines.append(f"**Reasoning:** {ds.reasoning}")
        lines.append("")

    if not ds.findings:
        lines.append("No findings.")
        lines.append("")
        return "\n".join(lines)

    for i, finding in enumerate(ds.findings, 1):
        severity = SEVERITY_LABELS.get(finding.severity, finding.severity.value)
        lines.append(f"**Finding {i} ({severity} severity):** {finding.description}")

        if finding.transcript_excerpt:
            lines.append(f"  - *Transcript:* \"{finding.transcript_excerpt}\"")
        if finding.note_excerpt:
            lines.append(f"  - *Note:* \"{finding.note_excerpt}\"")
        if finding.clinical_impact:
            lines.append(f"  - *Clinical impact:* {finding.clinical_impact}")
        lines.append("")

    return "\n".join(lines)


def render_markdown(
    report: EvaluationReport,
    output_path: Path | None = None,
) -> str:
    """Render an evaluation report as formatted Markdown."""
    lines = []

    # Header
    lines.append("# Scribeval Evaluation Report")
    lines.append("")
    lines.append(f"**Report ID:** {report.report_id}")
    lines.append(f"**Case:** {report.case_id}")
    candidate_label = report.candidate_label or report.scribe_product
    if candidate_label:
        lines.append(f"**Candidate Label:** {candidate_label}")
    lines.append(f"**Consultation Type:** {report.consultation_type}")
    lines.append(f"**Evaluated:** {report.timestamp.isoformat()}")
    lines.append(f"**Scribeval Version:** {report.scribeval_version}")
    lines.append("")

    # Preserve the report model's use limitations in the human-readable export.
    lines.append("## Use limitations")
    lines.append("")
    lines.append(report.notice)
    lines.append("")

    # Overall score
    severity_label = SEVERITY_LABELS.get(
        report.overall_severity, report.overall_severity.value
    )
    lines.append(
        f"## Overall Score: {report.overall_score:.2f} / 1.00 "
        f"({severity_label} severity)"
    )
    lines.append("")
    lines.append(_score_bar(report.overall_score))
    lines.append("")

    # Summary
    lines.append(report.summary)
    lines.append("")

    # Dimension score table
    lines.append("## Dimension Scores")
    lines.append("")
    lines.append("| Dimension | Score | Severity | Findings |")
    lines.append("|-----------|-------|----------|----------|")
    for ds in report.dimension_scores:
        severity = SEVERITY_LABELS.get(ds.severity_summary, ds.severity_summary.value)
        dim_name = ds.dimension.replace("_", " ").title()
        lines.append(
            f"| {dim_name} | {ds.score:.2f} | {severity} | "
            f"{len(ds.findings)} finding(s) |"
        )
    lines.append("")

    # Detailed findings per dimension
    lines.append("## Detailed Findings")
    lines.append("")
    for ds in report.dimension_scores:
        lines.append(_render_dimension(ds))

    # Export the existing provenance fields without raw judge responses.
    lines.append("## Provenance and run configuration")
    lines.append("")
    if report.reproducibility is None:
        lines.append(
            "Reproducibility metadata was not recorded; input and "
            "configuration identity is unverified."
        )
    else:
        lines.append("```json")
        lines.append(report.reproducibility.model_dump_json(indent=2))
        lines.append("```")
    lines.append("")

    lines.append("## Repeated-run uncertainty")
    lines.append("")
    if report.run_statistics:
        lines.append(
            "These intervals describe repeated judge-run variability for this note; "
            "they do not estimate population-level clinical performance."
        )
        lines.append("")
        lines.append("| Dimension | Runs | Mean | Standard deviation | Reported 95% interval |")
        lines.append("|-----------|------|------|--------------------|-----------------------|")
        for stats in report.run_statistics:
            if stats.run_count < 2:
                lines.append(
                    f"| {stats.dimension} | {stats.run_count} | {stats.mean_score:.4f} | "
                    "Not estimable | Not estimable (fewer than two runs) |"
                )
            else:
                lines.append(
                    f"| {stats.dimension} | {stats.run_count} | {stats.mean_score:.4f} | "
                    f"{stats.std_score:.4f} | [{stats.ci95_low:.4f}, {stats.ci95_high:.4f}] |"
                )
    else:
        lines.append("Repeated-run uncertainty was not recorded.")
    lines.append("")

    # Data flow disclosure
    lines.append("---")
    lines.append("")
    lines.append("## Data Flow Disclosure")
    lines.append("")
    lines.append(report.data_flow_disclosure)
    lines.append("")

    md = "\n".join(lines)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(md)

    return md
