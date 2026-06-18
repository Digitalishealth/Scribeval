"""Build the committed synthetic validation evidence-run bundle.

This script creates deterministic synthetic reviewer inputs in a temporary
directory, builds the public bundle, and indexes evidence runs. It intentionally
does not publish the raw worksheet, reviewer registry, or assignment worksheets.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from build_reviewer_assignments import build_assignments  # noqa: E402
from build_validation_evidence_bundle import build_bundle  # noqa: E402
from index_validation_evidence_runs import build_index, report_markdown, write_json  # noqa: E402

RUN_ID = "synthetic_bootstrap_v1"
BENCHMARK_UNIT = "whole transcript -> final note quality score"
CORPUS_MANIFEST = ROOT / "validation_pack" / "corpus" / "corpus_manifest.json"
PROTOCOL = ROOT / "validation_pack" / "clinician_review_protocol.json"
WORKSHEET_TEMPLATE = ROOT / "validation_pack" / "reviewer_worksheet.csv"
DEFAULT_OUTPUT_DIR = ROOT / "validation_pack" / "evidence_runs"
REQUIRED_DIMENSIONS = ("omission", "hallucination", "medicolegal", "ahpra", "pdqi9", "qnote")
REVIEWER_IDS = ("reviewer_clinician_001", "reviewer_clinician_002")
PROMPT_BASE_SCORES = {
    "cdss_checklist": 0.78,
    "standard": 0.58,
    "structured_soap": 0.70,
    "safety_first": 0.86,
    "cdss_informed": 0.90,
}
DIMENSION_FAILURES = {
    "omission": {
        "asthma_action_plan_gap",
        "clinically_significant_omission",
        "diabetes_safety_net_gap",
        "medication_adherence_gap",
        "preventive_care_followup_gap",
        "results_followup_ownership_gap",
    },
    "hallucination": {
        "over_inference_from_uncertain_transcript",
        "unsupported_hallucination",
    },
    "medicolegal": {
        "confidentiality_documentation_gap",
        "documentation_photo_gap",
        "medicolegal_followup_gap",
        "results_followup_ownership_gap",
        "work_certificate_documentation_gap",
    },
    "ahpra": {
        "confidentiality_documentation_gap",
        "culturally_safe_care_gap",
        "over_inference_from_uncertain_transcript",
        "unsupported_hallucination",
    },
    "pdqi9": {
        "clinically_significant_omission",
        "medication_dosing_risk",
        "unsupported_hallucination",
    },
    "qnote": {
        "clinically_significant_omission",
        "delirium_escalation_gap",
        "medicolegal_followup_gap",
        "renal_medication_interaction",
    },
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def worksheet_fields() -> list[str]:
    with WORKSHEET_TEMPLATE.open(newline="") as handle:
        return list(csv.DictReader(handle).fieldnames or [])


def write_reviewer_registry(path: Path) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "reviewer_id",
                "profession",
                "country",
                "registration_status",
                "years_post_registration",
                "specialty",
                "review_role",
                "conflict_of_interest",
                "training_completed",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "reviewer_id": REVIEWER_IDS[0],
                "profession": "general_practitioner",
                "country": "AU",
                "registration_status": "current",
                "years_post_registration": "8",
                "specialty": "general_practice",
                "review_role": "primary_reviewer",
                "conflict_of_interest": "none",
                "training_completed": "yes",
            }
        )
        writer.writerow(
            {
                "reviewer_id": REVIEWER_IDS[1],
                "profession": "general_practitioner",
                "country": "AU",
                "registration_status": "current",
                "years_post_registration": "12",
                "specialty": "general_practice",
                "review_role": "secondary_reviewer",
                "conflict_of_interest": "none",
                "training_completed": "yes",
            }
        )


def score_to_severity(score: float) -> str:
    if score >= 0.90:
        return "none"
    if score >= 0.75:
        return "low"
    if score >= 0.55:
        return "moderate"
    if score >= 0.35:
        return "high"
    return "critical"


def clipped_score(value: float) -> float:
    return round(min(0.98, max(0.08, value)), 2)


def dimension_score(note: dict[str, Any], case_failure_modes: set[str], dimension: str) -> float:
    failure_modes = case_failure_modes | set(note.get("seeded_failure_modes", []))
    score = PROMPT_BASE_SCORES[str(note["prompt_strategy"])]
    if note["note_source"] == "nurse_cdss":
        score += 0.03
    if failure_modes & DIMENSION_FAILURES[dimension]:
        score -= 0.22
    if note.get("seeded_failure_modes"):
        score -= 0.04
    if case_failure_modes and note["prompt_strategy"] == "safety_first":
        score += 0.04
    if note["prompt_strategy"] == "cdss_informed":
        score += 0.03
    return clipped_score(score)


def reviewer_adjustment(reviewer_id: str, dimension: str) -> float:
    if reviewer_id == REVIEWER_IDS[0]:
        return -0.02 if dimension in {"omission", "medicolegal", "qnote"} else 0.0
    return 0.02 if dimension in {"hallucination", "ahpra", "pdqi9"} else 0.0


def overall_score(dimension_scores: dict[str, float]) -> float:
    return clipped_score(sum(dimension_scores.values()) / len(dimension_scores))


def write_worksheet_and_judge_scores(worksheet: Path, judge_scores: Path) -> None:
    manifest = load_json(CORPUS_MANIFEST)
    judge_rows: list[dict[str, object]] = []
    fields = worksheet_fields()
    with worksheet.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for rel_path in manifest["case_files"]:
            case = load_json(CORPUS_MANIFEST.parent / rel_path)
            case_failure_modes = set(case.get("safety_failure_modes", []))
            for note in case["candidate_notes"]:
                scores = {
                    dimension: dimension_score(note, case_failure_modes, dimension)
                    for dimension in REQUIRED_DIMENSIONS
                }
                overall = overall_score(scores)
                for dimension, score in scores.items():
                    judge_rows.append(
                        {
                            "case_id": case["case_id"],
                            "submission_id": note["submission_id"],
                            "dimension": dimension,
                            "judge_score": clipped_score(score + 0.01),
                            "judge_severity": score_to_severity(score),
                            "overall_score": clipped_score(overall + 0.01),
                            "overall_severity": score_to_severity(overall),
                        }
                    )
                for reviewer_id in REVIEWER_IDS:
                    row = {field: "" for field in fields}
                    reviewer_scores = {
                        dimension: clipped_score(
                            score + reviewer_adjustment(reviewer_id, dimension)
                        )
                        for dimension, score in scores.items()
                    }
                    reviewer_overall = overall_score(reviewer_scores)
                    row.update(
                        {
                            "case_id": case["case_id"],
                            "blinded_submission": note["blind_label"],
                            "reviewer_id": reviewer_id,
                            "overall_score": f"{reviewer_overall:.2f}",
                            "overall_severity": score_to_severity(reviewer_overall),
                            "reviewer_comments": "",
                        }
                    )
                    for dimension, score in reviewer_scores.items():
                        row[f"{dimension}_score"] = f"{score:.2f}"
                        row[f"{dimension}_severity"] = score_to_severity(score)
                    writer.writerow(row)
    judge_scores.write_text(json.dumps(judge_rows, indent=2) + "\n")


def build_synthetic_bundle(output_dir: Path, *, clean: bool) -> Path:
    bundle_dir = output_dir / RUN_ID
    if bundle_dir.exists():
        if not clean:
            raise ValueError(f"bundle already exists: {bundle_dir}")
        shutil.rmtree(bundle_dir)

    with tempfile.TemporaryDirectory(prefix="scribeval-synthetic-bundle-") as tmp:
        temp_dir = Path(tmp)
        registry = temp_dir / "synthetic_bootstrap_reviewer_registry.csv"
        worksheet = temp_dir / "synthetic_bootstrap_worksheet.csv"
        judge_scores = temp_dir / "synthetic_bootstrap_judge_scores.json"
        assignments_dir = temp_dir / "synthetic_bootstrap_reviewer_assignments"

        write_reviewer_registry(registry)
        write_worksheet_and_judge_scores(worksheet, judge_scores)
        build_assignments(
            reviewer_registry=registry,
            output_dir=assignments_dir,
            corpus_manifest=CORPUS_MANIFEST,
            protocol=PROTOCOL,
            worksheet_template=WORKSHEET_TEMPLATE,
            seed=20260605,
        )
        bundle_dir = build_bundle(
            run_id=RUN_ID,
            worksheet=worksheet,
            reviewer_registry=registry,
            judge_scores=judge_scores,
            output_dir=output_dir,
            corpus_manifest=CORPUS_MANIFEST,
            protocol=PROTOCOL,
            evidence_status="synthetic_bootstrap",
            reviewer_assignments_dir=assignments_dir,
        )

    manifest_path = bundle_dir / "evidence_manifest.json"
    manifest = load_json(manifest_path)
    manifest["disclaimer"] = (
        "Synthetic bootstrap reviewer ratings only. This bundle is a public "
        "reproducibility artifact for the evidence-run workflow, not independent "
        "clinical validation."
    )
    manifest["input_generation"] = {
        "script": "python scripts/build_synthetic_evidence_bundle.py",
        "raw_inputs_public": False,
        "raw_input_policy": (
            "The synthetic worksheet, reviewer registry, and reviewer assignment "
            "worksheets are generated deterministically in a temporary directory "
            "and are not committed to the public evidence bundle."
        ),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    index = build_index(output_dir)
    write_json(output_dir / "index.json", index)
    (output_dir / "index.md").write_text(report_markdown(index))
    return bundle_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the synthetic bootstrap validation evidence bundle."
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="Fail instead of replacing an existing synthetic bootstrap bundle.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        bundle_dir = build_synthetic_bundle(args.output_dir, clean=not args.no_clean)
    except ValueError as exc:
        print(f"Synthetic bundle build failed: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote synthetic validation evidence bundle to {bundle_dir}")
    print(f"Benchmark unit: {BENCHMARK_UNIT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
