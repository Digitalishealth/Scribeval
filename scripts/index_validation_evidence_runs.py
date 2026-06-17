"""Index generated validation evidence run bundles.

The index is a publication-facing summary. It reads generated bundle artifacts
only and intentionally does not ingest raw clinician worksheets or registries.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE_RUNS = ROOT / "validation_pack" / "evidence_runs"
BENCHMARK_UNIT = "whole transcript -> final note quality score"


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} is not valid JSON: {exc}") from exc


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def resolve_bundle_path(bundle_dir: Path, manifest_value: str | None) -> Path | None:
    if not manifest_value:
        return None
    path = Path(manifest_value)
    if path.is_absolute():
        return path
    return (bundle_dir / path).resolve()


def find_bundle_dirs(evidence_runs: Path) -> list[Path]:
    if not evidence_runs.exists():
        return []
    if not evidence_runs.is_dir():
        raise ValueError(f"evidence runs path is not a directory: {evidence_runs}")
    return sorted(
        child
        for child in evidence_runs.iterdir()
        if child.is_dir() and (child / "evidence_manifest.json").exists()
    )


def optional_json(bundle_dir: Path, manifest: dict[str, Any], key: str) -> Any | None:
    path = resolve_bundle_path(bundle_dir, manifest.get(key))
    if path is None or not path.exists():
        return None
    return load_json(path)


def failed_check_count(claim_readiness: dict[str, Any] | None) -> int | None:
    if claim_readiness is None:
        return None
    failed_checks = claim_readiness.get("failed_checks")
    if isinstance(failed_checks, list):
        return len(failed_checks)
    checks = claim_readiness.get("checks", [])
    if not isinstance(checks, list):
        return None
    return sum(1 for check in checks if check.get("passed") is not True)


def min_check_observed(
    claim_readiness: dict[str, Any] | None,
    check_prefix: str,
) -> float | None:
    if claim_readiness is None:
        return None
    values: list[float] = []
    for check in claim_readiness.get("checks", []):
        if not isinstance(check, dict):
            continue
        check_id = check.get("id")
        observed = check.get("observed")
        if (
            isinstance(check_id, str)
            and check_id.startswith(check_prefix)
            and isinstance(observed, int | float)
        ):
            values.append(float(observed))
    return min(values) if values else None


def coverage_value(
    *,
    claim_readiness: dict[str, Any] | None,
    manifest_coverage: dict[str, Any],
    claim_key: str,
    manifest_key: str,
) -> int | None:
    if claim_readiness is not None:
        coverage = claim_readiness.get("coverage", {})
        value = coverage.get(claim_key) if isinstance(coverage, dict) else None
        if isinstance(value, int):
            return value
    value = manifest_coverage.get(manifest_key)
    return value if isinstance(value, int) else None


def index_bundle(bundle_dir: Path) -> dict[str, Any]:
    manifest = load_json(bundle_dir / "evidence_manifest.json")
    if not isinstance(manifest, dict):
        raise ValueError(f"{bundle_dir / 'evidence_manifest.json'} is not a JSON object")

    claim_readiness = optional_json(bundle_dir, manifest, "validation_claim_readiness")
    if claim_readiness is not None and not isinstance(claim_readiness, dict):
        raise ValueError(f"{bundle_dir.name} validation_claim_readiness is not an object")

    manifest_coverage = manifest.get("coverage", {})
    if not isinstance(manifest_coverage, dict):
        manifest_coverage = {}

    is_claim_ready = (
        bool(claim_readiness.get("is_ready_for_validation_claim"))
        if claim_readiness is not None
        else False
    )

    return {
        "evidence_id": manifest.get("evidence_id", bundle_dir.name),
        "status": manifest.get("status"),
        "bundle_path": display_path(bundle_dir),
        "benchmark_unit": manifest.get("benchmark_unit"),
        "is_ready_for_validation_claim": is_claim_ready,
        "failed_check_count": failed_check_count(claim_readiness),
        "case_count": coverage_value(
            claim_readiness=claim_readiness,
            manifest_coverage=manifest_coverage,
            claim_key="case_count",
            manifest_key="case_count",
        ),
        "submission_count": coverage_value(
            claim_readiness=claim_readiness,
            manifest_coverage=manifest_coverage,
            claim_key="submission_count",
            manifest_key="case_submission_count",
        ),
        "individual_calibration_pair_count": coverage_value(
            claim_readiness=claim_readiness,
            manifest_coverage=manifest_coverage,
            claim_key="individual_calibration_pair_count",
            manifest_key="calibration_pair_count",
        ),
        "consensus_calibration_pair_count": coverage_value(
            claim_readiness=claim_readiness,
            manifest_coverage=manifest_coverage,
            claim_key="consensus_pair_count",
            manifest_key="consensus_calibration_pair_count",
        ),
        "reviewer_reliability_pair_count": coverage_value(
            claim_readiness=claim_readiness,
            manifest_coverage=manifest_coverage,
            claim_key="reviewer_reliability_pair_count",
            manifest_key="reviewer_reliability_pair_count",
        ),
        "adjudication_required_count": coverage_value(
            claim_readiness=claim_readiness,
            manifest_coverage=manifest_coverage,
            claim_key="adjudication_required_count",
            manifest_key="consensus_adjudication_required_count",
        ),
        "min_reviewer_reliability_weighted_kappa": min_check_observed(
            claim_readiness,
            "reviewer_reliability.",
        ),
        "min_consensus_weighted_kappa": min_check_observed(
            claim_readiness,
            "consensus_agreement.",
        ),
    }


def build_index(evidence_runs: Path) -> dict[str, Any]:
    runs = [index_bundle(bundle_dir) for bundle_dir in find_bundle_dirs(evidence_runs)]
    return {
        "schema_version": "1.0.0",
        "index_id": "validation_evidence_runs_index_v1",
        "benchmark_unit": BENCHMARK_UNIT,
        "run_count": len(runs),
        "claim_ready_run_count": sum(
            1 for run in runs if run["is_ready_for_validation_claim"]
        ),
        "runs": runs,
    }


def format_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.3f}"
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value)


def report_markdown(index: dict[str, Any]) -> str:
    lines = [
        "# Validation Evidence Run Index",
        "",
        f"Benchmark unit: {index['benchmark_unit']}",
        f"Runs: {index['run_count']}",
        f"Claim-ready runs: {index['claim_ready_run_count']}",
        "",
        (
            "| Evidence ID | Status | Claim ready | Cases | Submissions | "
            "Consensus pairs | Reviewer kappa min | Consensus kappa min | Failed checks |"
        ),
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for run in index["runs"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    format_cell(run["evidence_id"]),
                    format_cell(run["status"]),
                    format_cell(run["is_ready_for_validation_claim"]),
                    format_cell(run["case_count"]),
                    format_cell(run["submission_count"]),
                    format_cell(run["consensus_calibration_pair_count"]),
                    format_cell(run["min_reviewer_reliability_weighted_kappa"]),
                    format_cell(run["min_consensus_weighted_kappa"]),
                    format_cell(run["failed_check_count"]),
                ]
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build an index of generated validation evidence run bundles."
    )
    parser.add_argument(
        "--evidence-runs",
        type=Path,
        default=DEFAULT_EVIDENCE_RUNS,
        help="Directory containing generated evidence run bundle directories.",
    )
    parser.add_argument("--output-json", required=True, type=Path)
    parser.add_argument("--output-md", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        index = build_index(args.evidence_runs)
    except ValueError as exc:
        print(f"Evidence run index failed: {exc}", file=sys.stderr)
        return 1

    write_json(args.output_json, index)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(report_markdown(index))
    print(f"Indexed validation evidence runs: {index['run_count']}")
    print(f"Claim-ready runs: {index['claim_ready_run_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
