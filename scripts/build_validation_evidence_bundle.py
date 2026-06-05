"""Build a reproducible validation evidence bundle from clinician review inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

DEFAULT_CORPUS_MANIFEST = ROOT / "validation_pack" / "corpus" / "corpus_manifest.json"
DEFAULT_PROTOCOL = ROOT / "validation_pack" / "clinician_review_protocol.json"
RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,80}$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative_or_name(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.name


def relative_to_base(path: Path, base: Path) -> str:
    return os.path.relpath(path.resolve(), start=base.resolve())


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def validate_run_id(run_id: str) -> None:
    if not RUN_ID_RE.fullmatch(run_id):
        raise ValueError(
            "run_id must be 1 to 81 characters and contain only letters, numbers, "
            "dot, underscore, and hyphen"
        )


def calibration_report_markdown(*, run_id: str, pairs: list[dict[str, Any]]) -> str:
    from scribeval.calibration import RatingPair, compute_agreement

    rating_pairs = [
        RatingPair(
            dimension=pair["dimension"],
            judge_score=float(pair["judge_score"]),
            human_score=float(pair["human_score"]),
            judge_severity=str(pair["judge_severity"]),
            human_severity=str(pair["human_severity"]),
        )
        for pair in pairs
    ]
    agreements = compute_agreement(rating_pairs)
    lines = [
        f"# Validation Calibration Report: {run_id}",
        "",
        "This report compares Scribeval transcript-to-note scores with clinician",
        "reviewer ratings for the same blinded case-submissions.",
        "",
        "## Agreement Summary",
        "",
        (
            "| Dimension | N | Weighted kappa | Kappa interpretation | "
            "ICC(2,1) | Mean absolute difference |"
        ),
        "|---|---:|---:|---|---:|---:|",
    ]
    for agreement in agreements:
        lines.append(
            f"| {agreement.dimension} | {agreement.n_pairs} | {agreement.kappa:.3f} | "
            f"{agreement.interpret_kappa()} | {agreement.icc:.3f} | "
            f"{agreement.mean_abs_difference:.3f} |"
        )
    return "\n".join(lines) + "\n"


def bundle_manifest(
    *,
    run_id: str,
    evidence_status: str,
    worksheet: Path,
    reviewer_registry: Path,
    judge_scores: Path,
    corpus_manifest: Path,
    protocol: Path,
    bundle_dir: Path,
    readiness_report: dict[str, Any],
    pair_count: int,
) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "evidence_id": run_id,
        "status": evidence_status,
        "benchmark_unit": "whole transcript -> final note quality score",
        "disclaimer": (
            "Independent clinician validation claims require a ready clinician "
            "review readiness report and qualified reviewer provenance."
        ),
        "corpus_manifest": relative_to_base(corpus_manifest, bundle_dir),
        "reviewer_worksheet": relative_or_name(worksheet),
        "reviewer_registry": relative_or_name(reviewer_registry),
        "judge_scores": relative_or_name(judge_scores),
        "calibration_pairs": "calibration_pairs.json",
        "calibration_report": "calibration_report.md",
        "readiness_report": "readiness_report.json",
        "readiness_report_markdown": "readiness_report.md",
        "stratified_summary": "stratified_summary.json",
        "stratified_summary_report": "stratified_summary.md",
        "generated_by": "python scripts/build_validation_evidence_bundle.py",
        "source_hashes": {
            "reviewer_worksheet_sha256": sha256_file(worksheet),
            "reviewer_registry_sha256": sha256_file(reviewer_registry),
            "judge_scores_sha256": sha256_file(judge_scores),
            "corpus_manifest_sha256": sha256_file(corpus_manifest),
            "protocol_sha256": sha256_file(protocol),
        },
        "coverage": {
            "case_submission_count": readiness_report["coverage"][
                "expected_case_submission_count"
            ],
            "complete_case_submission_count": readiness_report["coverage"][
                "complete_case_submission_count"
            ],
            "qualified_reviewer_count": readiness_report["coverage"][
                "qualified_reviewer_count"
            ],
            "calibration_pair_count": pair_count,
        },
    }


def build_bundle(
    *,
    run_id: str,
    worksheet: Path,
    reviewer_registry: Path,
    judge_scores: Path,
    output_dir: Path,
    corpus_manifest: Path,
    protocol: Path,
    evidence_status: str,
) -> Path:
    from audit_clinician_review_readiness import audit_readiness, report_markdown
    from import_validation_ratings import (
        build_pairs,
        load_blind_label_map,
        load_judge_scores,
        load_reviewer_registry,
    )
    from summarize_validation_evidence import report_markdown as stratified_report_markdown
    from summarize_validation_evidence import summarize

    validate_run_id(run_id)
    bundle_dir = output_dir / run_id
    bundle_dir.mkdir(parents=True, exist_ok=True)

    readiness = audit_readiness(
        worksheet_path=worksheet,
        reviewer_registry_path=reviewer_registry,
        corpus_manifest_path=corpus_manifest,
        protocol_path=protocol,
    )
    if not readiness["is_ready_for_independent_validation"]:
        write_json(bundle_dir / "readiness_report.json", readiness)
        (bundle_dir / "readiness_report.md").write_text(report_markdown(readiness))
        raise ValueError(
            "Clinician review inputs are not ready. See readiness_report.json in "
            f"{bundle_dir}"
        )

    registry = load_reviewer_registry(reviewer_registry)
    pairs = build_pairs(
        worksheet,
        load_judge_scores(judge_scores),
        load_blind_label_map(corpus_manifest),
        registry,
    )
    manifest = bundle_manifest(
        run_id=run_id,
        evidence_status=evidence_status,
        worksheet=worksheet,
        reviewer_registry=reviewer_registry,
        judge_scores=judge_scores,
        corpus_manifest=corpus_manifest,
        protocol=protocol,
        bundle_dir=bundle_dir,
        readiness_report=readiness,
        pair_count=len(pairs),
    )

    write_json(bundle_dir / "readiness_report.json", readiness)
    (bundle_dir / "readiness_report.md").write_text(report_markdown(readiness))
    write_json(bundle_dir / "calibration_pairs.json", pairs)
    (bundle_dir / "calibration_report.md").write_text(
        calibration_report_markdown(run_id=run_id, pairs=pairs)
    )
    write_json(bundle_dir / "evidence_manifest.json", manifest)

    summary = summarize(bundle_dir / "evidence_manifest.json")
    write_json(bundle_dir / "stratified_summary.json", summary)
    (bundle_dir / "stratified_summary.md").write_text(stratified_report_markdown(summary))
    return bundle_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a validation evidence bundle from completed clinician review inputs."
    )
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--worksheet", required=True, type=Path)
    parser.add_argument("--reviewer-registry", required=True, type=Path)
    parser.add_argument("--judge-scores", required=True, type=Path)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "validation_pack" / "evidence_runs",
        help="Parent directory for the run bundle.",
    )
    parser.add_argument("--corpus-manifest", type=Path, default=DEFAULT_CORPUS_MANIFEST)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument(
        "--status",
        default="independent_clinician_review",
        help="Evidence status to write into evidence_manifest.json.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        bundle_dir = build_bundle(
            run_id=args.run_id,
            worksheet=args.worksheet,
            reviewer_registry=args.reviewer_registry,
            judge_scores=args.judge_scores,
            output_dir=args.output_dir,
            corpus_manifest=args.corpus_manifest,
            protocol=args.protocol,
            evidence_status=args.status,
        )
    except ValueError as exc:
        print(f"Bundle build failed: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote validation evidence bundle to {bundle_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
