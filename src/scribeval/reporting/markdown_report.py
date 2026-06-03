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
