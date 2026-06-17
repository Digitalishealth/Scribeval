"""Build blinded adjudication packets for disputed consensus ratings.

Consensus rating rows can be structurally valid while still requiring
clinician adjudication. This script turns those disputed rows into a focused
worksheet and case packets without exposing reviewer identifiers or candidate
source metadata to the adjudicator.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS_MANIFEST = ROOT / "validation_pack" / "corpus" / "corpus_manifest.json"
DEFAULT_OUTPUT_DIR = ROOT / "validation_pack" / "adjudication_packets"
BENCHMARK_UNIT = "whole transcript -> final note quality score"

ADJUDICATION_FIELDS = [
    "case_id",
    "blinded_submission",
    "dimension",
    "reviewer_count",
    "reviewer_score_min",
    "reviewer_score_max",
    "reviewer_score_range",
    "reviewer_severity_values",
    "reviewer_severity_gap",
    "adjudicator_score",
    "adjudicator_severity",
    "adjudication_decision",
    "adjudicator_comments",
]


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


def transcript_markdown(turns: list[dict[str, str]]) -> list[str]:
    lines: list[str] = []
    for turn in turns:
        lines.append(f"**{turn['speaker'].strip()}:** {turn['text'].strip()}")
        lines.append("")
    return lines


def load_corpus(corpus_manifest: Path) -> dict[str, Any]:
    manifest = load_json(corpus_manifest)
    corpus_root = corpus_manifest.parent
    cases: dict[str, dict[str, Any]] = {}
    submissions: dict[tuple[str, str], dict[str, Any]] = {}
    submissions_by_id: dict[tuple[str, str], dict[str, Any]] = {}

    for rel_path in manifest.get("case_files", []):
        case = load_json(corpus_root / rel_path)
        case_id = case["case_id"]
        cases[case_id] = case
        for submission in case.get("candidate_notes", []):
            submissions[(case_id, submission["blind_label"])] = submission
            submissions_by_id[(case_id, submission["submission_id"])] = submission
    return {
        "manifest": manifest,
        "cases": cases,
        "submissions": submissions,
        "submissions_by_id": submissions_by_id,
    }


def disputed_pairs(consensus_pairs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        pair
        for pair in consensus_pairs
        if isinstance(pair, dict) and pair.get("adjudication_required") is True
    ]


def resolve_submission(
    pair: dict[str, Any],
    corpus: dict[str, Any],
) -> dict[str, Any]:
    case_id = pair.get("case_id")
    blind_label = pair.get("blind_label")
    submission_id = pair.get("submission_id")
    submission = corpus["submissions"].get((case_id, blind_label))
    if submission is None and submission_id:
        submission = corpus["submissions_by_id"].get((case_id, submission_id))
    if submission is None:
        raise ValueError(f"Unknown corpus submission for {case_id}/{blind_label}")
    return submission


def validate_pair(pair: dict[str, Any], corpus: dict[str, Any]) -> None:
    case_id = pair.get("case_id")
    if case_id not in corpus["cases"]:
        raise ValueError(f"Unknown corpus case in consensus pair: {case_id}")
    resolve_submission(pair, corpus)
    for key in (
        "dimension",
        "reviewer_count",
        "reviewer_score_min",
        "reviewer_score_max",
        "reviewer_score_range",
        "reviewer_severity_values",
        "reviewer_severity_gap",
    ):
        if key not in pair:
            raise ValueError(f"Consensus pair missing {key}")


def worksheet_row(pair: dict[str, Any], corpus: dict[str, Any]) -> dict[str, Any]:
    submission = resolve_submission(pair, corpus)
    return {
        "case_id": pair["case_id"],
        "blinded_submission": submission["blind_label"],
        "dimension": pair["dimension"],
        "reviewer_count": pair["reviewer_count"],
        "reviewer_score_min": pair["reviewer_score_min"],
        "reviewer_score_max": pair["reviewer_score_max"],
        "reviewer_score_range": pair["reviewer_score_range"],
        "reviewer_severity_values": ";".join(pair["reviewer_severity_values"]),
        "reviewer_severity_gap": pair["reviewer_severity_gap"],
        "adjudicator_score": "",
        "adjudicator_severity": "",
        "adjudication_decision": "",
        "adjudicator_comments": "",
    }


def write_worksheet(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ADJUDICATION_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def case_packet_markdown(
    *,
    case: dict[str, Any],
    pairs: list[dict[str, Any]],
    corpus: dict[str, Any],
) -> str:
    lines = [
        f"# Scribeval Adjudication Packet: {case['title']}",
        "",
        f"Case ID: `{case['case_id']}`",
        f"Setting: {case['setting']}",
        f"Acuity: {case['acuity']}",
        f"Consultation type: {case['consultation_type']}",
        "",
        "## Adjudicator Task",
        "",
        (
            "Resolve only the disputed dimensions listed below. Score each blinded "
            "final note against the whole transcript, not against another note."
        ),
        "",
        "## Transcript",
        "",
    ]
    lines.extend(transcript_markdown(case["transcript"]))
    lines.extend(
        [
            "## Disputed Candidate Notes",
            "",
        ]
    )

    pairs_by_label: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for pair in pairs:
        submission = resolve_submission(pair, corpus)
        pairs_by_label[submission["blind_label"]].append(pair)

    for blind_label, label_pairs in sorted(pairs_by_label.items()):
        submission = corpus["submissions"][(case["case_id"], blind_label)]
        lines.extend(
            [
                f"### {blind_label}",
                "",
                submission["note"].strip(),
                "",
                "| Dimension | Reviewer score range | Reviewer severity values |",
                "|---|---:|---|",
            ]
        )
        for pair in sorted(label_pairs, key=lambda item: item["dimension"]):
            severities = ", ".join(pair["reviewer_severity_values"])
            lines.append(
                f"| {pair['dimension']} | {pair['reviewer_score_min']}-"
                f"{pair['reviewer_score_max']} | {severities} |"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_packets(
    *,
    output_dir: Path,
    pairs: list[dict[str, Any]],
    corpus: dict[str, Any],
) -> list[str]:
    cases_dir = output_dir / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)
    pairs_by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for pair in pairs:
        pairs_by_case[pair["case_id"]].append(pair)

    packet_files: list[str] = []
    for case_id, case_pairs in sorted(pairs_by_case.items()):
        case = corpus["cases"][case_id]
        packet_rel_path = Path("cases") / f"{case_id}.md"
        packet_path = output_dir / packet_rel_path
        packet_path.write_text(
            case_packet_markdown(case=case, pairs=case_pairs, corpus=corpus)
        )
        packet_files.append(packet_rel_path.as_posix())

    expected_names = {Path(path).name for path in packet_files}
    for stale_path in cases_dir.glob("*.md"):
        if stale_path.name not in expected_names:
            stale_path.unlink()
    return packet_files


def readme_markdown() -> str:
    return (
        "# Adjudication Packets\n\n"
        "These packets are generated from consensus clinician rating rows where "
        "`adjudication_required` is true. They preserve blinding by showing case IDs, "
        "blinded submission labels, disputed dimensions, score ranges, and severity "
        "values without reviewer identifiers, note source labels, prompt strategies, "
        "or seeded failure metadata.\n"
    )


def build_adjudication_packets(
    *,
    consensus_pairs_path: Path,
    corpus_manifest: Path,
    output_dir: Path,
) -> dict[str, Any]:
    raw_pairs = load_json(consensus_pairs_path)
    if not isinstance(raw_pairs, list):
        raise ValueError("Consensus pairs input must be a JSON list")
    corpus = load_corpus(corpus_manifest)
    pairs = disputed_pairs(raw_pairs)
    for pair in pairs:
        validate_pair(pair, corpus)

    worksheet_rows = [worksheet_row(pair, corpus) for pair in pairs]
    worksheet_path = output_dir / "adjudication_worksheet.csv"
    write_worksheet(worksheet_path, worksheet_rows)
    packet_files = write_packets(output_dir=output_dir, pairs=pairs, corpus=corpus)
    (output_dir / "README.md").write_text(readme_markdown())

    manifest = {
        "schema_version": "1.0.0",
        "packet_id": "scribeval_adjudication_packets_v1",
        "benchmark_unit": BENCHMARK_UNIT,
        "source_consensus_pairs": display_path(consensus_pairs_path),
        "source_corpus_manifest": display_path(corpus_manifest),
        "adjudication_item_count": len(pairs),
        "case_count": len({pair["case_id"] for pair in pairs}),
        "submission_count": len(
            {
                f"{pair['case_id']}:{resolve_submission(pair, corpus)['blind_label']}"
                for pair in pairs
            }
        ),
        "dimensions": sorted({pair["dimension"] for pair in pairs}),
        "worksheet": "adjudication_worksheet.csv",
        "packet_files": packet_files,
        "blinding": {
            "hidden_fields": [
                "reviewer_ids",
                "submission_id",
                "note_source",
                "prompt_strategy",
                "seeded_failure_modes",
            ],
            "visible_fields": [
                "case_id",
                "blinded_submission",
                "dimension",
                "reviewer_score_range",
                "reviewer_severity_values",
            ],
        },
    }
    write_json(output_dir / "adjudication_manifest.json", manifest)
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build blinded adjudication packets for disputed consensus ratings."
    )
    parser.add_argument("--consensus-pairs", required=True, type=Path)
    parser.add_argument("--corpus-manifest", type=Path, default=DEFAULT_CORPUS_MANIFEST)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        manifest = build_adjudication_packets(
            consensus_pairs_path=args.consensus_pairs,
            corpus_manifest=args.corpus_manifest,
            output_dir=args.output_dir,
        )
    except ValueError as exc:
        print(f"Adjudication packet build failed: {exc}", file=sys.stderr)
        return 1

    print(f"Adjudication items: {manifest['adjudication_item_count']}")
    print(f"Wrote adjudication packets to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
