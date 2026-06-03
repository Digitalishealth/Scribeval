"""Render multi-case benchmark reports."""

from __future__ import annotations

from pathlib import Path

from scribeval.benchmark import BenchmarkReport


def render_benchmark_json(
    report: BenchmarkReport,
    output_path: Path | None = None,
) -> str:
    """Render a benchmark report as formatted JSON."""
    json_str = report.model_dump_json(indent=2)
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json_str)
    return json_str


def render_benchmark_markdown(
    report: BenchmarkReport,
    output_path: Path | None = None,
) -> str:
    """Render a benchmark report as Markdown."""
    lines: list[str] = [
        "# Scribeval Benchmark Report",
        "",
        f"**Benchmark ID:** {report.benchmark_id}",
        f"**Cases:** {report.case_count}",
        f"**Generated:** {report.timestamp.isoformat()}",
        "",
        "## Overall Ranking",
        "",
        "| Rank | Submission | Mean Score | Score SD | Cases | Critical Findings |",
        "|------|------------|------------|----------|-------|-------------------|",
    ]

    for rank, (label, mean_score) in enumerate(report.ranking, start=1):
        summary = report.submission_summaries[label]
        lines.append(
            f"| {rank} | {label} | {mean_score:.3f} | "
            f"{summary.std_overall_score:.3f} | {summary.case_count} | "
            f"{summary.critical_finding_count} |"
        )

    lines.extend(["", "## Per-Case Scores", ""])

    case_ids = [case_result.case_id for case_result in report.case_results]
    header = "| Submission | " + " | ".join(case_ids) + " |"
    separator = "|------------|" + "|".join(["---"] * len(case_ids)) + "|"
    lines.extend([header, separator])
    for label, _mean_score in report.ranking:
        summary = report.submission_summaries[label]
        scores = [
            f"{summary.scores_by_case.get(case_id, 0.0):.3f}"
            for case_id in case_ids
        ]
        lines.append(f"| {label} | " + " | ".join(scores) + " |")

    lines.extend(["", "## Dimension Means", ""])
    for label, _mean_score in report.ranking:
        summary = report.submission_summaries[label]
        lines.extend(
            [
                f"### {label}",
                "",
                "| Dimension | Mean Score |",
                "|-----------|------------|",
            ]
        )
        for dimension, score in summary.dimension_mean_scores.items():
            dimension_label = dimension.replace("_", " ").title()
            lines.append(f"| {dimension_label} | {score:.3f} |")
        lines.append("")

    lines.extend(
        [
            "## Notes",
            "",
            "- Every case must include the same submission labels for a fair aggregate.",
            "- Each case is scored as a blinded transcript-to-note comparison.",
            "- Mean score ranks products; score SD shows cross-case stability.",
            "- Critical findings count the highest-severity safety findings across all cases.",
            "",
        ]
    )

    markdown = "\n".join(lines)
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown)
    return markdown
