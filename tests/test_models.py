"""Tests for Pydantic data models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from scribeval.models.case import (
    ConsultationType,
    EvaluationCase,
    ReferenceNote,
    ScribeNote,
    Transcript,
)
from scribeval.models.report import DimensionStatistics, EvaluationReport
from scribeval.models.score import DimensionScore, Evidence, SeverityLevel


class TestTranscript:
    def test_basic_creation(self):
        t = Transcript(content="Doctor: Hello\nPatient: Hi")
        assert t.content == "Doctor: Hello\nPatient: Hi"
        assert t.source_format == "text"
        assert t.speaker_labels is False

    def test_empty_content_rejected(self):
        with pytest.raises(ValidationError):
            Transcript(content="")


class TestScribeNote:
    def test_basic_creation(self):
        note = ScribeNote(content="Assessment: Viral URTI", scribe_product="heidi")
        assert note.content == "Assessment: Viral URTI"
        assert note.scribe_product == "heidi"

    def test_optional_fields(self):
        note = ScribeNote(content="Note content")
        assert note.scribe_product is None
        assert note.scribe_version is None
        assert note.generation_timestamp is None

    def test_empty_content_rejected(self):
        with pytest.raises(ValidationError):
            ScribeNote(content="")


class TestReferenceNote:
    def test_basic_creation(self):
        ref = ReferenceNote(content="Gold standard note", author_role="Specialist")
        assert ref.author_role == "Specialist"
        assert ref.review_status == "unreviewed"


class TestEvaluationCase:
    def test_full_case(self):
        case = EvaluationCase(
            case_id="test_001",
            consultation_type=ConsultationType.GP_STANDARD,
            transcript=Transcript(content="transcript text"),
            scribe_note=ScribeNote(content="note text"),
            reference_note=ReferenceNote(content="reference text"),
        )
        assert case.case_id == "test_001"
        assert case.consultation_type == ConsultationType.GP_STANDARD
        assert case.reference_note is not None

    def test_case_without_reference(self):
        case = EvaluationCase(
            case_id="test_002",
            consultation_type=ConsultationType.ED_PRESENTATION,
            transcript=Transcript(content="transcript"),
            scribe_note=ScribeNote(content="note"),
        )
        assert case.reference_note is None

    def test_empty_case_id_rejected(self):
        with pytest.raises(ValidationError):
            EvaluationCase(
                case_id="",
                consultation_type=ConsultationType.GP_STANDARD,
                transcript=Transcript(content="text"),
                scribe_note=ScribeNote(content="text"),
            )

    def test_metadata_default_empty(self):
        case = EvaluationCase(
            case_id="test",
            consultation_type=ConsultationType.GP_STANDARD,
            transcript=Transcript(content="t"),
            scribe_note=ScribeNote(content="n"),
        )
        assert case.metadata == {}


class TestConsultationType:
    def test_all_types_exist(self):
        expected = {
            "gp_standard",
            "gp_long",
            "gp_telehealth",
            "ed_presentation",
            "specialist_review",
            "psychiatry",
            "paediatrics",
            "allied_health",
        }
        actual = {t.value for t in ConsultationType}
        assert actual == expected


class TestEvidence:
    def test_basic_creation(self):
        e = Evidence(
            description="Penicillin allergy omitted",
            severity=SeverityLevel.CRITICAL,
            transcript_excerpt="I'm allergic to penicillin",
            clinical_impact="Risk of allergic reaction if penicillin prescribed",
        )
        assert e.severity == SeverityLevel.CRITICAL

    def test_optional_fields(self):
        e = Evidence(description="Minor finding", severity=SeverityLevel.LOW)
        assert e.transcript_excerpt is None
        assert e.note_excerpt is None
        assert e.clinical_impact is None


class TestDimensionScore:
    def test_valid_score(self):
        ds = DimensionScore(
            dimension="omission",
            score=0.75,
            confidence=0.85,
            severity_summary=SeverityLevel.MODERATE,
            reasoning="Test reasoning",
            rubric_version="1.0.0",
            judge_type="mock",
        )
        assert ds.score == 0.75
        assert ds.dimension == "omission"

    def test_score_bounds(self):
        with pytest.raises(ValidationError):
            DimensionScore(
                dimension="test",
                score=1.5,
                confidence=0.5,
                severity_summary=SeverityLevel.NONE,
                reasoning="r",
                rubric_version="1.0",
                judge_type="mock",
            )

        with pytest.raises(ValidationError):
            DimensionScore(
                dimension="test",
                score=-0.1,
                confidence=0.5,
                severity_summary=SeverityLevel.NONE,
                reasoning="r",
                rubric_version="1.0",
                judge_type="mock",
            )

    def test_confidence_bounds(self):
        with pytest.raises(ValidationError):
            DimensionScore(
                dimension="test",
                score=0.5,
                confidence=1.5,
                severity_summary=SeverityLevel.NONE,
                reasoning="r",
                rubric_version="1.0",
                judge_type="mock",
            )


class TestSeverityLevel:
    def test_ordering(self):
        levels = list(SeverityLevel)
        assert levels == [
            SeverityLevel.NONE,
            SeverityLevel.LOW,
            SeverityLevel.MODERATE,
            SeverityLevel.HIGH,
            SeverityLevel.CRITICAL,
        ]


class TestEvaluationReport:
    def test_serialisation_roundtrip(self):
        report = EvaluationReport(
            report_id="test_report",
            case_id="test_case",
            consultation_type="gp_standard",
            dimension_scores=[
                DimensionScore(
                    dimension="omission",
                    score=0.8,
                    confidence=0.9,
                    severity_summary=SeverityLevel.LOW,
                    reasoning="Good capture",
                    rubric_version="1.0.0",
                    judge_type="mock",
                )
            ],
            overall_score=0.8,
            overall_severity=SeverityLevel.LOW,
            summary="Good overall",
            data_flow_disclosure="Local evaluation only.",
            scribeval_version="0.1.0",
        )
        json_str = report.model_dump_json()
        restored = EvaluationReport.model_validate_json(json_str)
        assert restored.report_id == "test_report"
        assert restored.overall_score == 0.8


class TestDimensionStatistics:
    def test_basic_creation(self):
        stats = DimensionStatistics(
            dimension="omission",
            mean=0.75,
            std=0.1,
            median=0.76,
            min_score=0.6,
            max_score=0.9,
            critical_finding_count=0,
            case_scores=[0.6, 0.76, 0.9],
        )
        assert stats.mean == 0.75
        assert len(stats.case_scores) == 3
