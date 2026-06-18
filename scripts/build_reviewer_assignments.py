"""Build balanced reviewer assignment worksheets for clinician validation."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS_MANIFEST = ROOT / "validation_pack" / "corpus" / "corpus_manifest.json"
DEFAULT_PROTOCOL = ROOT / "validation_pack" / "clinician_review_protocol.json"
DEFAULT_WORKSHEET_TEMPLATE = ROOT / "validation_pack" / "reviewer_worksheet.csv"
DEFAULT_OUTPUT_DIR = ROOT / "validation_pack" / "reviewer_assignments"
SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9_.-]+")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.name


def safe_filename(value: str) -> str:
    filename = SAFE_FILENAME_RE.sub("_", value).strip("._")
    if not filename:
        raise ValueError("reviewer_id cannot be converted to a safe filename")
    return filename


def reviewer_worksheet_fields(template_path: Path) -> list[str]:
    with template_path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
    if not fields:
        raise ValueError(f"{template_path} has no CSV header")
    return fields


def load_protocol_requirements(protocol_path: Path) -> dict[str, Any]:
    protocol = load_json(protocol_path)
    requirements = protocol.get("minimum_independent_review_requirements", {})
    return {
        "reviewers_per_case_submission": int(
            requirements.get(
                "reviewers_per_case_submission",
                requirements.get("reviewers_per_case", 2),
            )
        ),
        "required_dimensions": list(requirements.get("required_dimensions", [])),
    }


def load_case_submissions(corpus_manifest_path: Path) -> list[dict[str, str]]:
    manifest = load_json(corpus_manifest_path)
    corpus_root = corpus_manifest_path.parent
    assignments: list[dict[str, str]] = []
    for rel_path in manifest["case_files"]:
        case = load_json(corpus_root / rel_path)
        for submission in case["candidate_notes"]:
            assignments.append(
                {
                    "case_id": case["case_id"],
                    "blind_label": submission["blind_label"],
                    "specialty": case["specialty"],
                    "setting": case["setting"],
                }
            )
    if not assignments:
        raise ValueError("Corpus manifest did not resolve any blinded submissions")
    return assignments


def load_qualified_reviewers(
    reviewer_registry_path: Path,
    protocol_path: Path,
) -> list[str]:
    from audit_clinician_review_readiness import load_protocol, load_reviewer_registry

    protocol = load_protocol(protocol_path)
    registry = load_reviewer_registry(reviewer_registry_path, protocol)
    reviewer_ids = sorted(registry)
    if not reviewer_ids:
        raise ValueError("Reviewer registry has no qualified reviewers")
    return reviewer_ids


def build_assignment_rows(
    *,
    case_submissions: list[dict[str, str]],
    reviewer_ids: list[str],
    reviewers_per_case_submission: int,
    seed: int,
) -> list[dict[str, str]]:
    if reviewers_per_case_submission < 1:
        raise ValueError("reviewers_per_case_submission must be >= 1")
    if len(reviewer_ids) < reviewers_per_case_submission:
        raise ValueError(
            "Reviewer registry does not contain enough qualified reviewers for "
            f"{reviewers_per_case_submission} reviewers per case-submission"
        )

    rng = random.Random(seed)
    reviewer_order = reviewer_ids[:]
    rng.shuffle(reviewer_order)

    rows: list[dict[str, str]] = []
    for index, submission in enumerate(case_submissions):
        selected = [
            reviewer_order[(index + offset) % len(reviewer_order)]
            for offset in range(reviewers_per_case_submission)
        ]
        for reviewer_id in selected:
            rows.append(
                {
                    "case_id": submission["case_id"],
                    "blinded_submission": submission["blind_label"],
                    "reviewer_id": reviewer_id,
                }
            )
    return rows


def write_reviewer_worksheets(
    *,
    rows: list[dict[str, str]],
    output_dir: Path,
    fieldnames: list[str],
) -> list[dict[str, Any]]:
    worksheets_dir = output_dir / "worksheets"
    worksheets_dir.mkdir(parents=True, exist_ok=True)
    rows_by_reviewer: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        rows_by_reviewer[row["reviewer_id"]].append(row)

    worksheet_files: list[dict[str, Any]] = []
    expected_filenames: set[str] = set()
    for reviewer_id, reviewer_rows in sorted(rows_by_reviewer.items()):
        rel_path = Path("worksheets") / f"{safe_filename(reviewer_id)}.csv"
        worksheet_path = output_dir / rel_path
        expected_filenames.add(worksheet_path.name)
        with worksheet_path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for reviewer_row in reviewer_rows:
                row = {field: "" for field in fieldnames}
                row.update(reviewer_row)
                writer.writerow(row)
        worksheet_files.append(
            {
                "reviewer_id": reviewer_id,
                "path": rel_path.as_posix(),
                "assignment_count": len(reviewer_rows),
            }
        )

    for stale_path in worksheets_dir.glob("*.csv"):
        if stale_path.name not in expected_filenames:
            stale_path.unlink()
    return worksheet_files


def assignment_manifest(
    *,
    rows: list[dict[str, str]],
    reviewer_ids: list[str],
    worksheet_files: list[dict[str, Any]],
    corpus_manifest: Path,
    protocol: Path,
    reviewer_registry: Path,
    seed: int,
    reviewers_per_case_submission: int,
) -> dict[str, Any]:
    reviewers_by_submission: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        key = f"{row['case_id']}:{row['blinded_submission']}"
        reviewers_by_submission[key].add(row["reviewer_id"])
    return {
        "schema_version": "1.0.0",
        "assignment_id": "scribeval_reviewer_assignments_v1",
        "benchmark_unit": "whole transcript -> final note quality score",
        "seed": seed,
        "reviewers_per_case_submission": reviewers_per_case_submission,
        "case_submission_count": len(reviewers_by_submission),
        "assignment_count": len(rows),
        "reviewer_count": len(reviewer_ids),
        "reviewer_ids": reviewer_ids,
        "worksheet_files": worksheet_files,
        "source_files": {
            "corpus_manifest": display_path(corpus_manifest),
            "clinician_review_protocol": display_path(protocol),
            "reviewer_registry": reviewer_registry.name,
        },
        "source_hashes": {
            "corpus_manifest_sha256": sha256_file(corpus_manifest),
            "clinician_review_protocol_sha256": sha256_file(protocol),
            "reviewer_registry_sha256": sha256_file(reviewer_registry),
        },
        "case_submission_reviewers": {
            key: sorted(value) for key, value in sorted(reviewers_by_submission.items())
        },
    }


def readme_text() -> str:
    lines = [
        "# Reviewer Assignments",
        "",
        "This directory is generated by `python scripts/build_reviewer_assignments.py`.",
        "",
        (
            "It contains one worksheet per pseudonymous reviewer plus an assignment "
            "manifest. Give each reviewer their own worksheet and the blinded packet "
            "files in `validation_pack/reviewer_packets/`."
        ),
        "",
        (
            "Do not add direct identifiers such as names, emails, phone numbers, "
            "provider numbers, or registration numbers."
        ),
    ]
    return "\n".join(lines) + "\n"


def build_assignments(
    *,
    reviewer_registry: Path,
    output_dir: Path,
    corpus_manifest: Path,
    protocol: Path,
    worksheet_template: Path,
    seed: int,
) -> Path:
    requirements = load_protocol_requirements(protocol)
    case_submissions = load_case_submissions(corpus_manifest)
    reviewer_ids = load_qualified_reviewers(reviewer_registry, protocol)
    rows = build_assignment_rows(
        case_submissions=case_submissions,
        reviewer_ids=reviewer_ids,
        reviewers_per_case_submission=requirements["reviewers_per_case_submission"],
        seed=seed,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    fieldnames = reviewer_worksheet_fields(worksheet_template)
    worksheet_files = write_reviewer_worksheets(
        rows=rows,
        output_dir=output_dir,
        fieldnames=fieldnames,
    )
    manifest = assignment_manifest(
        rows=rows,
        reviewer_ids=reviewer_ids,
        worksheet_files=worksheet_files,
        corpus_manifest=corpus_manifest,
        protocol=protocol,
        reviewer_registry=reviewer_registry,
        seed=seed,
        reviewers_per_case_submission=requirements["reviewers_per_case_submission"],
    )
    (output_dir / "README.md").write_text(readme_text())
    (output_dir / "assignment_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return output_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build balanced reviewer assignment worksheets for clinician validation."
    )
    parser.add_argument("--reviewer-registry", required=True, type=Path)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--corpus-manifest", type=Path, default=DEFAULT_CORPUS_MANIFEST)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--worksheet-template", type=Path, default=DEFAULT_WORKSHEET_TEMPLATE)
    parser.add_argument("--seed", type=int, default=20260605)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        output_dir = build_assignments(
            reviewer_registry=args.reviewer_registry,
            output_dir=args.output_dir,
            corpus_manifest=args.corpus_manifest,
            protocol=args.protocol,
            worksheet_template=args.worksheet_template,
            seed=args.seed,
        )
    except ValueError as exc:
        print(f"Assignment build failed: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote reviewer assignments to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
