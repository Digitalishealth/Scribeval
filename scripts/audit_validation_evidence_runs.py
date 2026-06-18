"""Audit publishable validation evidence run bundles.

This script is intentionally dependency-free. It checks generated clinician
validation evidence bundles for reproducibility metadata and rejects raw
clinician CSV inputs that should stay outside the public evidence trail.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE_RUNS = ROOT / "validation_pack" / "evidence_runs"

ALLOWED_STATUSES = {
    "independent_clinician_review",
    "pilot_independent_review",
    "synthetic_bootstrap",
}
BENCHMARK_UNIT = "whole transcript -> final note quality score"
REQUIRED_MANIFEST_FILES = (
    "readiness_report",
    "readiness_report_markdown",
    "calibration_pairs",
    "calibration_report",
    "consensus_calibration_pairs",
    "consensus_calibration_report",
    "stratified_summary",
    "stratified_summary_report",
    "reviewer_reliability",
    "reviewer_reliability_report",
    "validation_claim_readiness",
    "validation_claim_readiness_report",
)
REQUIRED_SOURCE_HASHES = {
    "corpus_manifest_sha256",
    "judge_scores_sha256",
    "protocol_sha256",
    "reviewer_registry_sha256",
    "reviewer_worksheet_sha256",
}
REQUIRED_STRATA = {"failure_mode", "note_source", "prompt_strategy", "specialty"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise AssertionError(f"{path} is not valid JSON: {exc}") from exc


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def resolve_bundle_path(bundle_dir: Path, manifest_value: str) -> Path:
    path = Path(manifest_value)
    if path.is_absolute():
        return path
    return (bundle_dir / path).resolve()


def find_bundle_dirs(evidence_runs: Path) -> list[Path]:
    if not evidence_runs.exists():
        return []
    require(evidence_runs.is_dir(), f"evidence runs path is not a directory: {evidence_runs}")
    return sorted(
        child
        for child in evidence_runs.iterdir()
        if child.is_dir() and (child / "evidence_manifest.json").exists()
    )


def audit_no_raw_clinician_inputs(bundle_dir: Path) -> None:
    for path in bundle_dir.rglob("*"):
        if not path.is_file():
            continue
        lower_name = path.name.lower()
        require(
            path.suffix.lower() != ".csv",
            f"{bundle_dir.name} contains raw clinician CSV input: {path.name}",
        )
        require(
            "reviewer_worksheet" not in lower_name
            and "reviewer_registry" not in lower_name,
            f"{bundle_dir.name} contains raw reviewer input file: {path.name}",
        )


def audit_source_hashes(bundle_name: str, manifest: dict[str, Any]) -> None:
    source_hashes = manifest.get("source_hashes")
    require(isinstance(source_hashes, dict), f"{bundle_name} missing source_hashes")
    expected_hashes = set(REQUIRED_SOURCE_HASHES)
    if manifest.get("consensus_source") == "adjudicated_consensus_pairs":
        expected_hashes.add("adjudicated_consensus_pairs_sha256")
        require(
            isinstance(manifest.get("adjudicated_consensus_pairs_source"), str)
            and manifest.get("adjudicated_consensus_pairs_source"),
            f"{bundle_name} missing adjudicated_consensus_pairs_source",
        )
    require(
        set(source_hashes) == expected_hashes,
        f"{bundle_name} source_hashes drift",
    )
    for key, value in source_hashes.items():
        require(isinstance(value, str), f"{bundle_name} {key} is not a string")
        require(SHA256_RE.fullmatch(value) is not None, f"{bundle_name} {key} is not sha256")


def audit_referenced_files(bundle_dir: Path, manifest: dict[str, Any]) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for key in REQUIRED_MANIFEST_FILES:
        value = manifest.get(key)
        require(isinstance(value, str) and value, f"{bundle_dir.name} missing {key}")
        path = resolve_bundle_path(bundle_dir, value)
        require(path.exists(), f"{bundle_dir.name} referenced file missing: {key}")
        paths[key] = path

    corpus_manifest = manifest.get("corpus_manifest")
    require(
        isinstance(corpus_manifest, str) and corpus_manifest,
        f"{bundle_dir.name} missing corpus_manifest",
    )
    corpus_manifest_path = resolve_bundle_path(bundle_dir, corpus_manifest)
    require(corpus_manifest_path.exists(), f"{bundle_dir.name} corpus_manifest is missing")
    paths["corpus_manifest"] = corpus_manifest_path
    return paths


def audit_readiness(
    bundle_name: str,
    readiness_path: Path,
    manifest: dict[str, Any],
) -> None:
    readiness = load_json(readiness_path)
    coverage = readiness.get("coverage", {})
    manifest_coverage = manifest.get("coverage", {})
    require(
        readiness.get("is_ready_for_independent_validation") is True,
        f"{bundle_name} readiness report is not ready",
    )
    require(
        coverage.get("complete_case_submission_count")
        == coverage.get("expected_case_submission_count"),
        f"{bundle_name} readiness coverage is incomplete",
    )
    require(
        coverage.get("qualified_reviewer_count", 0) >= 2,
        f"{bundle_name} has fewer than two qualified reviewers",
    )
    require(
        manifest_coverage.get("case_submission_count")
        == coverage.get("expected_case_submission_count"),
        f"{bundle_name} manifest case_submission_count drift",
    )
    require(
        manifest_coverage.get("complete_case_submission_count")
        == coverage.get("complete_case_submission_count"),
        f"{bundle_name} manifest complete_case_submission_count drift",
    )
    require(
        manifest_coverage.get("qualified_reviewer_count")
        == coverage.get("qualified_reviewer_count"),
        f"{bundle_name} manifest qualified_reviewer_count drift",
    )


def audit_pairs_and_summary(
    bundle_name: str,
    pairs_path: Path,
    consensus_pairs_path: Path,
    summary_path: Path,
    reviewer_reliability_path: Path,
    claim_readiness_path: Path,
    manifest: dict[str, Any],
) -> int:
    pairs = load_json(pairs_path)
    consensus_pairs = load_json(consensus_pairs_path)
    summary = load_json(summary_path)
    reviewer_reliability = load_json(reviewer_reliability_path)
    claim_readiness = load_json(claim_readiness_path)
    manifest_coverage = manifest.get("coverage", {})
    require(isinstance(pairs, list) and pairs, f"{bundle_name} has no calibration pairs")
    pair_count = len(pairs)
    require(
        manifest_coverage.get("calibration_pair_count") == pair_count,
        f"{bundle_name} manifest calibration_pair_count drift",
    )
    require(
        isinstance(consensus_pairs, list) and consensus_pairs,
        f"{bundle_name} has no consensus calibration pairs",
    )
    consensus_pair_count = len(consensus_pairs)
    require(
        manifest_coverage.get("consensus_calibration_pair_count") == consensus_pair_count,
        f"{bundle_name} manifest consensus_calibration_pair_count drift",
    )
    require(
        all("adjudication_required" in pair for pair in consensus_pairs),
        f"{bundle_name} consensus pairs missing adjudication flags",
    )
    if manifest.get("consensus_source") == "adjudicated_consensus_pairs":
        require(
            all(pair["adjudication_required"] is False for pair in consensus_pairs),
            f"{bundle_name} adjudicated consensus contains unresolved flags",
        )
    require(
        manifest_coverage.get("consensus_adjudication_required_count")
        == sum(1 for pair in consensus_pairs if pair["adjudication_required"]),
        f"{bundle_name} consensus adjudication count drift",
    )
    require(
        summary.get("benchmark_unit") == BENCHMARK_UNIT,
        f"{bundle_name} stratified summary has invalid benchmark_unit",
    )
    require(
        summary.get("coverage", {}).get("pair_count") == pair_count,
        f"{bundle_name} stratified summary pair_count drift",
    )
    strata = summary.get("strata")
    require(isinstance(strata, dict), f"{bundle_name} stratified summary missing strata")
    require(set(strata) >= REQUIRED_STRATA, f"{bundle_name} stratified summary strata drift")
    for stratum in REQUIRED_STRATA:
        rows = strata[stratum]
        require(isinstance(rows, list) and rows, f"{bundle_name} missing {stratum} rows")
    require(
        reviewer_reliability.get("benchmark_unit") == BENCHMARK_UNIT,
        f"{bundle_name} reviewer reliability has invalid benchmark_unit",
    )
    reliability_coverage = reviewer_reliability.get("coverage", {})
    require(
        reliability_coverage.get("reliability_pair_count")
        == manifest_coverage.get("reviewer_reliability_pair_count"),
        f"{bundle_name} reviewer reliability pair_count drift",
    )
    require(
        reliability_coverage.get("reliability_pair_count", 0) > 0,
        f"{bundle_name} reviewer reliability has no pairs",
    )
    reliability_strata = reviewer_reliability.get("strata")
    require(
        isinstance(reliability_strata, dict),
        f"{bundle_name} reviewer reliability missing strata",
    )
    require(
        set(reliability_strata) >= REQUIRED_STRATA,
        f"{bundle_name} reviewer reliability strata drift",
    )
    require(
        claim_readiness.get("benchmark_unit") == BENCHMARK_UNIT,
        f"{bundle_name} validation claim readiness has invalid benchmark_unit",
    )
    require(
        claim_readiness.get("evidence_id") == manifest.get("evidence_id"),
        f"{bundle_name} validation claim readiness evidence_id drift",
    )
    require(
        isinstance(claim_readiness.get("is_ready_for_validation_claim"), bool),
        f"{bundle_name} validation claim readiness missing status",
    )
    require(
        isinstance(claim_readiness.get("checks"), list)
        and claim_readiness.get("checks"),
        f"{bundle_name} validation claim readiness has no checks",
    )
    return pair_count


def audit_bundle(bundle_dir: Path) -> int:
    audit_no_raw_clinician_inputs(bundle_dir)
    manifest = load_json(bundle_dir / "evidence_manifest.json")
    require(
        manifest.get("benchmark_unit") == BENCHMARK_UNIT,
        f"{bundle_dir.name} has invalid benchmark_unit",
    )
    require(
        manifest.get("status") in ALLOWED_STATUSES,
        f"{bundle_dir.name} has unsupported evidence status",
    )
    audit_source_hashes(bundle_dir.name, manifest)
    paths = audit_referenced_files(bundle_dir, manifest)
    audit_readiness(bundle_dir.name, paths["readiness_report"], manifest)
    return audit_pairs_and_summary(
        bundle_dir.name,
        paths["calibration_pairs"],
        paths["consensus_calibration_pairs"],
        paths["stratified_summary"],
        paths["reviewer_reliability"],
        paths["validation_claim_readiness"],
        manifest,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit generated validation evidence run bundles."
    )
    parser.add_argument(
        "--evidence-runs",
        type=Path,
        default=DEFAULT_EVIDENCE_RUNS,
        help="Directory containing generated evidence run bundle directories.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        bundle_dirs = find_bundle_dirs(args.evidence_runs)
        pair_count = sum(audit_bundle(bundle_dir) for bundle_dir in bundle_dirs)
    except AssertionError as exc:
        print(f"Evidence run audit failed: {exc}", file=sys.stderr)
        return 1

    print("Evidence run audit passed.")
    print(f"Bundles: {len(bundle_dirs)}")
    print(f"Calibration pairs: {pair_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
