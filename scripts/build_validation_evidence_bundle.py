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
DEFAULT_REVIEWER_PACKETS = ROOT / "validation_pack" / "reviewer_packets"
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


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} is not valid JSON: {exc}") from exc


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


def consensus_report_markdown(*, run_id: str, pairs: list[dict[str, Any]]) -> str:
    from build_consensus_validation_ratings import consensus_summary, report_markdown

    summary = consensus_summary(pairs)
    report = report_markdown(summary)
    return report.replace(
        "# Clinician Consensus Validation Ratings",
        f"# Clinician Consensus Validation Ratings: {run_id}",
        1,
    )


def consensus_pair_key(pair: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(pair.get("case_id", "")),
        str(pair.get("submission_id", "")),
        str(pair.get("blind_label", "")),
        str(pair.get("dimension", "")),
    )


def load_adjudicated_consensus_pairs(
    *,
    adjudicated_consensus_pairs: Path,
    computed_consensus_pairs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    raw_pairs = load_json(adjudicated_consensus_pairs)
    if not isinstance(raw_pairs, list) or not raw_pairs:
        raise ValueError("--adjudicated-consensus-pairs must be a non-empty JSON list")
    pairs = [dict(pair) for pair in raw_pairs]
    computed_keys = {consensus_pair_key(pair) for pair in computed_consensus_pairs}
    adjudicated_keys = {consensus_pair_key(pair) for pair in pairs}
    if adjudicated_keys != computed_keys:
        missing = sorted(computed_keys - adjudicated_keys)
        extra = sorted(adjudicated_keys - computed_keys)
        if missing:
            key = missing[0]
            raise ValueError(
                "Adjudicated consensus pairs are missing "
                f"{key[0]}/{key[1]}/{key[3]}"
            )
        key = extra[0]
        raise ValueError(
            "Adjudicated consensus pairs contain unknown "
            f"{key[0]}/{key[1]}/{key[3]}"
        )
    for index, pair in enumerate(pairs, start=1):
        if "adjudication_required" not in pair:
            raise ValueError(f"Adjudicated consensus pair {index} missing adjudication flag")
        if pair.get("adjudication_required") is True:
            raise ValueError(
                "Adjudicated consensus pairs still contain unresolved adjudication "
                f"at row {index}"
            )
    return pairs


def build_review_materials_provenance(
    *,
    reviewer_packets_dir: Path,
    bundle_dir: Path,
) -> dict[str, Any]:
    manifest_path = reviewer_packets_dir / "reviewer_packet_manifest.json"
    if not manifest_path.exists():
        raise ValueError(f"Reviewer packet manifest is missing: {manifest_path}")
    packet_manifest = load_json(manifest_path)
    packet_files = packet_manifest.get("packet_files")
    if not isinstance(packet_files, list) or not packet_files:
        raise ValueError("Reviewer packet manifest has no packet_files")

    packet_hashes: dict[str, str] = {}
    for rel_path in packet_files:
        packet_path = reviewer_packets_dir / str(rel_path)
        if not packet_path.exists():
            raise ValueError(f"Reviewer packet file is missing: {packet_path}")
        packet_hashes[str(rel_path)] = sha256_file(packet_path)

    readme_path = reviewer_packets_dir / "README.md"
    return {
        "schema_version": "1.0.0",
        "provenance_id": "scribeval_review_materials_v1",
        "benchmark_unit": "whole transcript -> final note quality score",
        "reviewer_packets_dir": relative_to_base(reviewer_packets_dir, bundle_dir),
        "reviewer_packet_manifest": relative_to_base(manifest_path, bundle_dir),
        "reviewer_packet_manifest_sha256": sha256_file(manifest_path),
        "reviewer_packet_count": len(packet_hashes),
        "packet_files_sha256": packet_hashes,
        "readme_sha256": sha256_file(readme_path) if readme_path.exists() else None,
        "privacy_note": (
            "Reviewer material hashes identify the blinded packet files shown to "
            "clinicians. They do not include reviewer identifiers, assignment "
            "worksheets, reviewer comments, or completed ratings."
        ),
    }


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
    consensus_pair_count: int,
    consensus_adjudication_required_count: int,
    reviewer_reliability_pair_count: int,
    adjudicated_consensus_pairs: Path | None,
    reviewer_assignments_manifest: Path | None,
    review_materials: dict[str, Any],
) -> dict[str, Any]:
    source_hashes = {
        "reviewer_worksheet_sha256": sha256_file(worksheet),
        "reviewer_registry_sha256": sha256_file(reviewer_registry),
        "judge_scores_sha256": sha256_file(judge_scores),
        "corpus_manifest_sha256": sha256_file(corpus_manifest),
        "protocol_sha256": sha256_file(protocol),
        "reviewer_packet_manifest_sha256": review_materials[
            "reviewer_packet_manifest_sha256"
        ],
    }
    if adjudicated_consensus_pairs is not None:
        source_hashes["adjudicated_consensus_pairs_sha256"] = sha256_file(
            adjudicated_consensus_pairs
        )
    if reviewer_assignments_manifest is not None:
        source_hashes["reviewer_assignments_manifest_sha256"] = sha256_file(
            reviewer_assignments_manifest
        )

    manifest = {
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
        "consensus_calibration_pairs": "consensus_calibration_pairs.json",
        "consensus_calibration_report": "consensus_calibration_report.md",
        "consensus_source": (
            "adjudicated_consensus_pairs"
            if adjudicated_consensus_pairs is not None
            else "computed_from_reviewer_worksheet"
        ),
        "readiness_report": "readiness_report.json",
        "readiness_report_markdown": "readiness_report.md",
        "review_materials": "review_materials.json",
        "review_run_status": "review_run_status.json",
        "review_run_status_report": "review_run_status.md",
        "stratified_summary": "stratified_summary.json",
        "stratified_summary_report": "stratified_summary.md",
        "reviewer_reliability": "reviewer_reliability.json",
        "reviewer_reliability_report": "reviewer_reliability.md",
        "validation_claim_readiness": "validation_claim_readiness.json",
        "validation_claim_readiness_report": "validation_claim_readiness.md",
        "generated_by": "python scripts/build_validation_evidence_bundle.py",
        "source_hashes": source_hashes,
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
            "consensus_calibration_pair_count": consensus_pair_count,
            "consensus_adjudication_required_count": consensus_adjudication_required_count,
            "reviewer_reliability_pair_count": reviewer_reliability_pair_count,
        },
    }
    if adjudicated_consensus_pairs is not None:
        manifest["adjudicated_consensus_pairs_source"] = relative_or_name(
            adjudicated_consensus_pairs
        )
    if reviewer_assignments_manifest is not None:
        manifest["reviewer_assignments_manifest_source"] = relative_or_name(
            reviewer_assignments_manifest
        )
    return manifest


def resolve_assignment_manifest(assignments_dir: Path | None) -> Path | None:
    if assignments_dir is None:
        return None
    manifest = assignments_dir / "assignment_manifest.json"
    if not manifest.exists():
        raise ValueError(f"Reviewer assignments manifest is missing: {manifest}")
    return manifest


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
    adjudicated_consensus_pairs: Path | None = None,
    reviewer_assignments_dir: Path | None = None,
    reviewer_packets_dir: Path = DEFAULT_REVIEWER_PACKETS,
) -> Path:
    from assess_validation_claim_readiness import assess_claim_readiness
    from assess_validation_claim_readiness import report_markdown as claim_report_markdown
    from audit_clinician_review_readiness import audit_readiness, report_markdown
    from build_consensus_validation_ratings import build_consensus_pairs
    from import_validation_ratings import (
        build_pairs,
        load_blind_label_map,
        load_judge_scores,
        load_reviewer_registry,
    )
    from summarize_reviewer_reliability import report_markdown as reliability_report_markdown
    from summarize_reviewer_reliability import summarize_reviewer_reliability
    from summarize_validation_evidence import report_markdown as stratified_report_markdown
    from summarize_validation_evidence import summarize
    from summarize_validation_review_run import build_review_run_status
    from summarize_validation_review_run import report_markdown as review_run_status_markdown

    validate_run_id(run_id)
    bundle_dir = output_dir / run_id
    bundle_dir.mkdir(parents=True, exist_ok=True)
    reviewer_assignments_manifest = resolve_assignment_manifest(reviewer_assignments_dir)
    review_materials = build_review_materials_provenance(
        reviewer_packets_dir=reviewer_packets_dir,
        bundle_dir=bundle_dir,
    )

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
    review_run_status = build_review_run_status(
        reviewer_registry=reviewer_registry,
        worksheet=worksheet,
        judge_scores=judge_scores,
        assignments_dir=reviewer_assignments_dir,
        corpus_manifest=corpus_manifest,
        protocol_path=protocol,
    )

    registry = load_reviewer_registry(reviewer_registry)
    pairs = build_pairs(
        worksheet,
        load_judge_scores(judge_scores),
        load_blind_label_map(corpus_manifest),
        registry,
    )
    reviewer_reliability = summarize_reviewer_reliability(
        worksheet=worksheet,
        reviewer_registry=reviewer_registry,
        corpus_manifest=corpus_manifest,
        protocol=protocol,
    )
    computed_consensus_pairs = build_consensus_pairs(
        worksheet=worksheet,
        reviewer_registry=reviewer_registry,
        judge_scores_path=judge_scores,
        corpus_manifest=corpus_manifest,
        protocol=protocol,
    )
    consensus_pairs = (
        load_adjudicated_consensus_pairs(
            adjudicated_consensus_pairs=adjudicated_consensus_pairs,
            computed_consensus_pairs=computed_consensus_pairs,
        )
        if adjudicated_consensus_pairs is not None
        else computed_consensus_pairs
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
        consensus_pair_count=len(consensus_pairs),
        consensus_adjudication_required_count=sum(
            1 for pair in consensus_pairs if pair["adjudication_required"]
        ),
        reviewer_reliability_pair_count=reviewer_reliability["coverage"][
            "reliability_pair_count"
        ],
        adjudicated_consensus_pairs=adjudicated_consensus_pairs,
        reviewer_assignments_manifest=reviewer_assignments_manifest,
        review_materials=review_materials,
    )

    write_json(bundle_dir / "readiness_report.json", readiness)
    (bundle_dir / "readiness_report.md").write_text(report_markdown(readiness))
    write_json(bundle_dir / "review_materials.json", review_materials)
    write_json(bundle_dir / "review_run_status.json", review_run_status)
    (bundle_dir / "review_run_status.md").write_text(
        review_run_status_markdown(review_run_status)
    )
    write_json(bundle_dir / "calibration_pairs.json", pairs)
    (bundle_dir / "calibration_report.md").write_text(
        calibration_report_markdown(run_id=run_id, pairs=pairs)
    )
    write_json(bundle_dir / "consensus_calibration_pairs.json", consensus_pairs)
    (bundle_dir / "consensus_calibration_report.md").write_text(
        consensus_report_markdown(run_id=run_id, pairs=consensus_pairs)
    )
    write_json(bundle_dir / "evidence_manifest.json", manifest)
    write_json(bundle_dir / "reviewer_reliability.json", reviewer_reliability)
    (bundle_dir / "reviewer_reliability.md").write_text(
        reliability_report_markdown(reviewer_reliability)
    )

    summary = summarize(bundle_dir / "evidence_manifest.json")
    write_json(bundle_dir / "stratified_summary.json", summary)
    (bundle_dir / "stratified_summary.md").write_text(stratified_report_markdown(summary))
    claim_readiness = assess_claim_readiness(
        evidence_manifest_path=bundle_dir / "evidence_manifest.json",
        protocol_path=protocol,
    )
    write_json(bundle_dir / "validation_claim_readiness.json", claim_readiness)
    (bundle_dir / "validation_claim_readiness.md").write_text(
        claim_report_markdown(claim_readiness)
    )
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
    parser.add_argument("--reviewer-packets-dir", type=Path, default=DEFAULT_REVIEWER_PACKETS)
    parser.add_argument(
        "--status",
        default="independent_clinician_review",
        help="Evidence status to write into evidence_manifest.json.",
    )
    parser.add_argument(
        "--adjudicated-consensus-pairs",
        type=Path,
        help=(
            "Optional full consensus_calibration_pairs JSON after qualified "
            "adjudication decisions have been imported. The pair keyset must match "
            "the computed consensus pairs from the worksheet."
        ),
    )
    parser.add_argument(
        "--reviewer-assignments-dir",
        type=Path,
        help=(
            "Optional directory generated by build_reviewer_assignments.py. "
            "The evidence bundle records only assignment aggregate status and "
            "the assignment_manifest.json hash."
        ),
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
            adjudicated_consensus_pairs=args.adjudicated_consensus_pairs,
            reviewer_assignments_dir=args.reviewer_assignments_dir,
            reviewer_packets_dir=args.reviewer_packets_dir,
        )
    except ValueError as exc:
        print(f"Bundle build failed: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote validation evidence bundle to {bundle_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
