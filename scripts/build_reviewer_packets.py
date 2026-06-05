"""Build blinded clinician reviewer packets from the validation corpus."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS_MANIFEST = ROOT / "validation_pack" / "corpus" / "corpus_manifest.json"
DEFAULT_OUTPUT_DIR = ROOT / "validation_pack" / "reviewer_packets"

REVIEW_DIMENSIONS = [
    "omission",
    "hallucination",
    "medicolegal adequacy",
    "AHPRA compliance",
    "PDQI-9",
    "QNOTE",
    "optional AMT medication terminology",
]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def transcript_markdown(turns: list[dict[str, str]]) -> list[str]:
    lines: list[str] = []
    for turn in turns:
        speaker = turn["speaker"].strip()
        text = turn["text"].strip()
        lines.append(f"**{speaker}:** {text}")
        lines.append("")
    return lines


def candidate_notes_markdown(submissions: list[dict[str, Any]]) -> list[str]:
    lines = ["## Blinded Candidate Notes", ""]
    for submission in submissions:
        lines.append(f"### {submission['blind_label']}")
        lines.append("")
        lines.append(submission["note"].strip())
        lines.append("")
    return lines


def case_packet_markdown(case: dict[str, Any]) -> str:
    lines = [
        f"# Scribeval Reviewer Packet: {case['title']}",
        "",
        f"Case ID: `{case['case_id']}`",
        f"Setting: {case['setting']}",
        f"Acuity: {case['acuity']}",
        f"Consultation type: {case['consultation_type']}",
        "",
        "## Reviewer Task",
        "",
        (
            "Score each blinded final note against the whole transcript. Do not score "
            "a note against another note, and do not infer quality from submission order."
        ),
        "",
        "Review dimensions:",
        "",
    ]
    lines.extend(f"- {dimension}" for dimension in REVIEW_DIMENSIONS)
    lines.extend(["", "## Transcript", ""])
    lines.extend(transcript_markdown(case["transcript"]))
    lines.extend(candidate_notes_markdown(case["candidate_notes"]))
    return "\n".join(lines).rstrip() + "\n"


def readme_markdown() -> str:
    lines = [
        "# Blinded Reviewer Packets",
        "",
        "These packets are generated from the public validation corpus by:",
        "",
        "```bash",
        "python scripts/build_reviewer_packets.py",
        "```",
        "",
        (
            "Each case packet contains the transcript and blinded candidate notes that a "
            "clinician reviewer needs for independent scoring. Coordinator-only fields "
            "such as source identity, prompting details, and seeded failure labels are "
            "kept in the corpus JSON and omitted from these packet files."
        ),
        "",
        (
            "The note text is preserved verbatim. If a submitted note identifies its own "
            "workflow in the clinical prose, that prose remains visible because altering "
            "it would change the material being scored."
        ),
    ]
    return "\n".join(lines) + "\n"


def packet_manifest(
    *,
    case_count: int,
    packet_files: list[str],
    source_corpus: Path,
    output_dir: Path,
) -> dict[str, Any]:
    visible_labels = [f"Submission {letter}" for letter in "ABCDE"]
    try:
        source_corpus_ref = source_corpus.relative_to(output_dir)
    except ValueError:
        source_corpus_ref = Path("..") / "corpus" / "corpus_manifest.json"
    return {
        "schema_version": "1.0.0",
        "packet_id": "scribeval_reviewer_packets_v0",
        "source_corpus": source_corpus_ref.as_posix(),
        "case_count": case_count,
        "blinding": {
            "hidden_fields": [
                "submission_id",
                "note_source",
                "prompt_strategy",
                "seeded_failure_modes",
            ],
            "visible_submission_labels": visible_labels,
            "note_text_policy": (
                "Candidate note text is preserved verbatim. Workflow self-identification "
                "inside the note text remains visible because it is part of the scored note."
            ),
        },
        "packet_files": packet_files,
    }


def write_packets(corpus_manifest: Path, output_dir: Path) -> int:
    manifest = load_json(corpus_manifest)
    corpus_root = corpus_manifest.parent
    cases_dir = output_dir / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)

    packet_files: list[str] = []
    for rel_path in manifest["case_files"]:
        case = load_json(corpus_root / rel_path)
        packet_rel_path = Path("cases") / f"{case['case_id']}.md"
        packet_path = output_dir / packet_rel_path
        packet_path.write_text(case_packet_markdown(case))
        packet_files.append(packet_rel_path.as_posix())

    expected_names = {Path(path).name for path in packet_files}
    for stale_path in cases_dir.glob("*.md"):
        if stale_path.name not in expected_names:
            stale_path.unlink()

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "README.md").write_text(readme_markdown())
    packet_data = packet_manifest(
        case_count=len(packet_files),
        packet_files=packet_files,
        source_corpus=corpus_manifest,
        output_dir=output_dir,
    )
    (output_dir / "reviewer_packet_manifest.json").write_text(
        json.dumps(packet_data, indent=2) + "\n"
    )
    return len(packet_files)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build blinded reviewer packets from the validation corpus."
    )
    parser.add_argument(
        "--corpus-manifest",
        type=Path,
        default=DEFAULT_CORPUS_MANIFEST,
        help="Path to validation corpus_manifest.json.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where reviewer packets will be written.",
    )
    args = parser.parse_args()

    count = write_packets(args.corpus_manifest, args.output_dir)
    print(f"Wrote {count} reviewer packets to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
