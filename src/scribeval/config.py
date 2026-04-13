"""Configuration management via environment variables and defaults."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class ScribevalSettings(BaseSettings):
    """Scribeval configuration.

    All settings can be overridden via environment variables prefixed with
    SCRIBEVAL_ (e.g., SCRIBEVAL_ANTHROPIC_API_KEY, SCRIBEVAL_DEFAULT_MODEL).
    """

    model_config = SettingsConfigDict(env_prefix="SCRIBEVAL_")

    anthropic_api_key: str = ""
    default_model: str = "claude-sonnet-4-20250514"
    default_dimensions: list[str] = [
        "omission",
        "hallucination",
        "medicolegal",
        "ahpra",
        "pdqi9",
        "qnote",
    ]
    # FHIR R4 terminology server for the opt-in medication_terminology
    # evaluator. Fail-closed by default — callers MUST explicitly set
    # SCRIBEVAL_FHIR_TERMINOLOGY_URL (e.g., to a private Ontoserver or
    # the CSIRO public sandbox at https://r4.ontoserver.csiro.au/fhir)
    # before the medication terminology dimension will run. This prevents
    # accidental transmission of medication strings to a public service
    # as a side effect of a default setting.
    fhir_terminology_url: str | None = None
    fhir_timeout_seconds: float = 5.0
    rubric_dir: Path = Path("rubrics")
    output_dir: Path = Path("output")
    max_retries: int = 2
    verbose: bool = False


def get_settings() -> ScribevalSettings:
    """Load settings from environment."""
    return ScribevalSettings()
