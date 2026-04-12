"""Tests for the medication_terminology evaluator and FHIR terminology client.

These tests use a fully in-process fake FHIR client — they never make
real network calls. This is critical because the default FHIR endpoint
is the CSIRO public sandbox, and tests must remain hermetic and fast.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from scribeval.clients.fhir import (
    FHIRTerminologyClient,
    FHIRUnreachableError,
    ValidationOutcome,
    ValidationResult,
)
from scribeval.evaluators.medication_terminology import (
    EXTRACTION_PROMPT_TEMPLATE,
    ExtractedMedication,
    MedicationTerminologyEvaluator,
    is_safe_medication_string,
)
from scribeval.judges.base import BaseJudge
from scribeval.models.case import (
    ConsultationType,
    EvaluationCase,
    ScribeNote,
    Transcript,
)
from scribeval.models.score import SeverityLevel
from scribeval.rubrics.loader import load_rubric

RUBRICS_DIR = Path(__file__).parent.parent / "rubrics"


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


class StubJudge(BaseJudge):
    """A judge that returns a fixed extraction response."""

    def __init__(self, response: str):
        self._response = response

    @property
    def judge_type(self) -> str:
        return "stub"

    @property
    def judge_model(self) -> str | None:
        return "stub-1.0"

    def evaluate(self, prompt: str) -> str:
        return self._response


class FakeFHIRClient(FHIRTerminologyClient):
    """In-memory FHIR client. Maps medication query strings to outcomes."""

    def __init__(
        self,
        outcomes: dict[str, ValidationOutcome] | None = None,
        endpoint: str = "https://fake.example.org/fhir",
        unreachable: bool = False,
    ):
        super().__init__(endpoint=endpoint, timeout_seconds=1.0)
        self._outcomes = outcomes or {}
        self._unreachable = unreachable

    def validate_medication(self, medication: str) -> ValidationResult:
        if self._unreachable:
            raise FHIRUnreachableError("simulated network failure")
        outcome = self._outcomes.get(
            medication.strip().lower(), ValidationOutcome.INVALID
        )
        return ValidationResult(
            medication=medication,
            outcome=outcome,
            matched_display=medication if outcome != ValidationOutcome.INVALID else None,
            match_count=1 if outcome != ValidationOutcome.INVALID else 0,
        )


@pytest.fixture
def med_rubric():
    return load_rubric(RUBRICS_DIR / "medication_terminology.yaml")


def _make_case(scribe_text: str) -> EvaluationCase:
    return EvaluationCase(
        case_id="med_test",
        consultation_type=ConsultationType.GP_STANDARD,
        transcript=Transcript(content="Doctor: standard consult."),
        scribe_note=ScribeNote(content=scribe_text, scribe_product="test"),
    )


def _extraction_response(meds: list[dict]) -> str:
    return json.dumps({"medications": meds})


# ---------------------------------------------------------------------------
# Rubric load
# ---------------------------------------------------------------------------


class TestRubric:
    def test_loads(self, med_rubric):
        assert med_rubric.dimension == "medication_terminology"
        assert "AMT" in med_rubric.display_name
        # Severity levels match the loader contract
        assert set(med_rubric.severity_criteria.keys()) >= {
            "none",
            "low",
            "moderate",
            "high",
            "critical",
        }


# ---------------------------------------------------------------------------
# Extracted medication helpers
# ---------------------------------------------------------------------------


class TestExtractedMedication:
    def test_query_string_minimal(self):
        m = ExtractedMedication(name="amoxicillin", strength=None, form=None, context="")
        assert m.query_string() == "amoxicillin"

    def test_query_string_full(self):
        m = ExtractedMedication(
            name="amoxicillin",
            strength="500mg",
            form="capsule",
            context="new_prescription",
        )
        assert m.query_string() == "amoxicillin 500mg capsule"


# ---------------------------------------------------------------------------
# Defence-in-depth medication string sanitiser
# ---------------------------------------------------------------------------


class TestSafeMedicationString:
    @pytest.mark.parametrize(
        "s",
        [
            "amoxicillin",
            "amoxicillin 500mg",
            "co-amoxiclav 875/125",
            "Voltaren 25mg",
            "salbutamol (ventolin) 100mcg/dose",
        ],
    )
    def test_valid_medication_strings(self, s):
        assert is_safe_medication_string(s)

    @pytest.mark.parametrize(
        "s",
        [
            "",
            "x" * 201,
            "amoxicillin\n<script>",
            "drop table medications;",
            "amoxicillin' OR 1=1 --",
            "amoxicillin {injection}",
            "amoxicillin?id=1",
        ],
    )
    def test_unsafe_medication_strings(self, s):
        assert not is_safe_medication_string(s)


# ---------------------------------------------------------------------------
# FHIR client matching logic (using mocked httpx via transport)
# ---------------------------------------------------------------------------


class TestFHIRClientClassification:
    """Tests for the classification logic, isolated from real HTTP."""

    def _client_with_handler(self, handler):
        transport = httpx.MockTransport(handler)
        client = FHIRTerminologyClient(endpoint="https://fake.example.org/fhir")

        # Patch _expand_with_filter to use our transport
        def fake_expand(filter_text: str):
            with httpx.Client(transport=transport, timeout=1.0) as c:
                resp = c.get(
                    "https://fake.example.org/fhir/ValueSet/$expand",
                    params={"filter": filter_text},
                )
                resp.raise_for_status()
                return resp.json().get("expansion", {}).get("contains", [])

        client._expand_with_filter = fake_expand  # type: ignore[method-assign]
        return client

    def test_no_matches_is_invalid(self):
        def handler(request):
            return httpx.Response(200, json={"expansion": {"contains": []}})

        client = self._client_with_handler(handler)
        result = client.validate_medication("nonexistentdrug")
        assert result.outcome == ValidationOutcome.INVALID
        assert result.match_count == 0

    def test_single_exact_match_is_valid_exact(self):
        def handler(request):
            return httpx.Response(
                200,
                json={
                    "expansion": {
                        "contains": [{"display": "amoxicillin", "code": "1"}]
                    }
                },
            )

        client = self._client_with_handler(handler)
        result = client.validate_medication("amoxicillin")
        assert result.outcome == ValidationOutcome.VALID_EXACT
        assert result.matched_display == "amoxicillin"

    def test_single_substring_match_is_less_specific(self):
        def handler(request):
            return httpx.Response(
                200,
                json={
                    "expansion": {
                        "contains": [
                            {"display": "amoxicillin 500 mg capsule", "code": "1"}
                        ]
                    }
                },
            )

        client = self._client_with_handler(handler)
        result = client.validate_medication("amoxicillin")
        assert result.outcome == ValidationOutcome.VALID_LESS_SPECIFIC

    def test_multiple_matches_with_no_exact_is_ambiguous(self):
        def handler(request):
            return httpx.Response(
                200,
                json={
                    "expansion": {
                        "contains": [
                            {"display": "Panadol 500mg tablet"},
                            {"display": "Panadol Osteo 665mg tablet"},
                            {"display": "Panadol Extra 500/65mg tablet"},
                        ]
                    }
                },
            )

        client = self._client_with_handler(handler)
        result = client.validate_medication("panadol")
        assert result.outcome == ValidationOutcome.AMBIGUOUS
        assert result.match_count == 3

    def test_multiple_matches_with_exact_returns_exact(self):
        def handler(request):
            return httpx.Response(
                200,
                json={
                    "expansion": {
                        "contains": [
                            {"display": "amoxicillin"},
                            {"display": "amoxicillin 500mg capsule"},
                        ]
                    }
                },
            )

        client = self._client_with_handler(handler)
        result = client.validate_medication("amoxicillin")
        assert result.outcome == ValidationOutcome.VALID_EXACT


class TestFHIRClientErrors:
    def test_timeout_returns_lookup_failed(self):
        def handler(request):
            raise httpx.ReadTimeout("simulated timeout")

        transport = httpx.MockTransport(handler)
        client = FHIRTerminologyClient(endpoint="https://fake.example.org/fhir")

        def fake_expand(filter_text: str):
            with httpx.Client(transport=transport, timeout=0.5) as c:
                resp = c.get("https://fake.example.org/fhir/ValueSet/$expand")
                resp.raise_for_status()
                return []

        client._expand_with_filter = fake_expand  # type: ignore[method-assign]
        result = client.validate_medication("amoxicillin")
        assert result.outcome == ValidationOutcome.LOOKUP_FAILED

    def test_http_error_returns_lookup_failed(self):
        def handler(request):
            return httpx.Response(500, json={"error": "server down"})

        transport = httpx.MockTransport(handler)
        client = FHIRTerminologyClient(endpoint="https://fake.example.org/fhir")

        def fake_expand(filter_text: str):
            with httpx.Client(transport=transport, timeout=0.5) as c:
                resp = c.get("https://fake.example.org/fhir/ValueSet/$expand")
                resp.raise_for_status()
                return []

        client._expand_with_filter = fake_expand  # type: ignore[method-assign]
        result = client.validate_medication("amoxicillin")
        assert result.outcome == ValidationOutcome.LOOKUP_FAILED

    def test_connect_error_raises_unreachable(self):
        def handler(request):
            raise httpx.ConnectError("simulated DNS failure")

        transport = httpx.MockTransport(handler)
        client = FHIRTerminologyClient(endpoint="https://fake.example.org/fhir")

        def fake_expand(filter_text: str):
            with httpx.Client(transport=transport, timeout=0.5) as c:
                c.get("https://fake.example.org/fhir/ValueSet/$expand")
                return []

        client._expand_with_filter = fake_expand  # type: ignore[method-assign]
        with pytest.raises(FHIRUnreachableError):
            client.validate_medication("amoxicillin")


# ---------------------------------------------------------------------------
# MedicationTerminologyEvaluator integration
# ---------------------------------------------------------------------------


class TestMedicationTerminologyEvaluator:
    def test_no_fhir_client_returns_degraded(self, med_rubric):
        judge = StubJudge(_extraction_response([]))
        evaluator = MedicationTerminologyEvaluator(
            rubric=med_rubric, judge=judge, fhir_client=None
        )
        case = _make_case("Plan: amoxicillin 500mg TDS")
        result = evaluator.evaluate(case)
        assert result.score == 0.0
        assert result.confidence == 0.0
        assert result.severity_summary == SeverityLevel.LOW
        assert "FHIR client not configured" in result.findings[0].description

    def test_no_medications_extracted_is_perfect(self, med_rubric):
        judge = StubJudge(_extraction_response([]))
        fhir = FakeFHIRClient()
        evaluator = MedicationTerminologyEvaluator(
            rubric=med_rubric, judge=judge, fhir_client=fhir
        )
        case = _make_case("Plan: rest, fluids, review in 1 week.")
        result = evaluator.evaluate(case)
        assert result.score == 1.0
        assert result.confidence == 1.0
        assert result.severity_summary == SeverityLevel.NONE
        assert len(result.findings) == 1
        assert "No medications" in result.findings[0].description

    def test_all_valid_medications_full_score(self, med_rubric):
        judge = StubJudge(
            _extraction_response(
                [
                    {
                        "name": "amoxicillin",
                        "strength": "500mg",
                        "form": "capsule",
                        "context": "new_prescription",
                    },
                    {
                        "name": "paracetamol",
                        "strength": "500mg",
                        "form": "tablet",
                        "context": "current_medications",
                    },
                ]
            )
        )
        fhir = FakeFHIRClient(
            {
                "amoxicillin": ValidationOutcome.VALID_EXACT,
                "paracetamol": ValidationOutcome.VALID_EXACT,
            }
        )
        evaluator = MedicationTerminologyEvaluator(
            rubric=med_rubric, judge=judge, fhir_client=fhir
        )
        case = _make_case("Plan: amoxicillin 500mg TDS, continue paracetamol 500mg")
        result = evaluator.evaluate(case)
        assert result.score == 1.0
        assert result.confidence == 1.0
        assert result.severity_summary == SeverityLevel.NONE
        assert len(result.findings) == 2

    def test_invalid_medication_caps_score_at_half(self, med_rubric):
        judge = StubJudge(
            _extraction_response(
                [
                    {"name": "amoxicillin", "strength": None, "form": None, "context": ""},
                    {"name": "fakedrug", "strength": None, "form": None, "context": ""},
                ]
            )
        )
        fhir = FakeFHIRClient(
            {
                "amoxicillin": ValidationOutcome.VALID_EXACT,
                "fakedrug": ValidationOutcome.INVALID,
            }
        )
        evaluator = MedicationTerminologyEvaluator(
            rubric=med_rubric, judge=judge, fhir_client=fhir
        )
        case = _make_case("Plan: amoxicillin, fakedrug")
        result = evaluator.evaluate(case)
        # Mean would be (1.0 + 0.0) / 2 = 0.5; cap holds at 0.5
        assert result.score == 0.5
        assert result.severity_summary == SeverityLevel.CRITICAL

    def test_ambiguous_medication_high_severity(self, med_rubric):
        judge = StubJudge(
            _extraction_response(
                [{"name": "panadol", "strength": None, "form": None, "context": ""}]
            )
        )
        fhir = FakeFHIRClient({"panadol": ValidationOutcome.AMBIGUOUS})
        evaluator = MedicationTerminologyEvaluator(
            rubric=med_rubric, judge=judge, fhir_client=fhir
        )
        result = evaluator.evaluate(_make_case("Plan: panadol prn"))
        assert result.score == 0.3  # AMBIGUOUS score
        assert result.severity_summary == SeverityLevel.HIGH

    def test_fhir_unreachable_returns_degraded(self, med_rubric):
        judge = StubJudge(
            _extraction_response(
                [{"name": "amoxicillin", "strength": None, "form": None, "context": ""}]
            )
        )
        fhir = FakeFHIRClient(unreachable=True)
        evaluator = MedicationTerminologyEvaluator(
            rubric=med_rubric, judge=judge, fhir_client=fhir
        )
        result = evaluator.evaluate(_make_case("Plan: amoxicillin"))
        assert result.score == 0.0
        assert result.confidence == 0.0
        assert "FHIR endpoint unreachable" in result.findings[0].description

    def test_lookup_failed_lowers_confidence(self, med_rubric):
        judge = StubJudge(
            _extraction_response(
                [
                    {"name": "amoxicillin", "strength": None, "form": None, "context": ""},
                    {"name": "paracetamol", "strength": None, "form": None, "context": ""},
                ]
            )
        )
        fhir = FakeFHIRClient(
            {
                "amoxicillin": ValidationOutcome.VALID_EXACT,
                "paracetamol": ValidationOutcome.LOOKUP_FAILED,
            }
        )
        evaluator = MedicationTerminologyEvaluator(
            rubric=med_rubric, judge=judge, fhir_client=fhir
        )
        result = evaluator.evaluate(_make_case("Plan: amoxicillin, paracetamol"))
        # 1 of 2 lookups succeeded
        assert result.confidence == 0.5

    def test_malformed_extraction_response_degraded(self, med_rubric):
        judge = StubJudge("not even close to JSON")
        fhir = FakeFHIRClient()
        evaluator = MedicationTerminologyEvaluator(
            rubric=med_rubric, judge=judge, fhir_client=fhir
        )
        result = evaluator.evaluate(_make_case("Plan: anything"))
        assert result.score == 0.0
        assert "Failed to parse" in result.findings[0].description

    def test_extraction_prompt_does_not_include_transcript(self, med_rubric):
        """Privacy: the extraction prompt must use only the scribe note,
        never the transcript. Otherwise patient identifiers from the
        transcript could indirectly reach the FHIR layer through extraction
        side-effects."""
        judge = StubJudge(_extraction_response([]))
        evaluator = MedicationTerminologyEvaluator(
            rubric=med_rubric, judge=judge, fhir_client=FakeFHIRClient()
        )
        case = EvaluationCase(
            case_id="x",
            consultation_type=ConsultationType.GP_STANDARD,
            transcript=Transcript(content="SECRET_PHI_MARKER"),
            scribe_note=ScribeNote(content="Plan: amoxicillin 500mg"),
        )
        prompt = evaluator.build_prompt(case)
        assert "SECRET_PHI_MARKER" not in prompt
        assert "amoxicillin" in prompt

    def test_extraction_prompt_template_renders(self):
        rendered = EXTRACTION_PROMPT_TEMPLATE.format(note="Plan: amoxicillin")
        assert "amoxicillin" in rendered
        assert "JSON" in rendered
