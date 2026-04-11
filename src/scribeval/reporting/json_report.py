"""JSON report renderer."""

from __future__ import annotations

from pathlib import Path

from scribeval.models.report import AggregateReport, EvaluationReport


def render_json(
    report: EvaluationReport | AggregateReport,
    output_path: Path | None = None,
) -> str:
    """Render a report as formatted JSON.

    If output_path is provided, writes to file and returns the JSON string.
    Otherwise just returns the JSON string.
    """
    json_str = report.model_dump_json(indent=2)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json_str)

    return json_str
