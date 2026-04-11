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
    rubric_dir: Path = Path("rubrics")
    output_dir: Path = Path("output")
    max_retries: int = 2
    verbose: bool = False


def get_settings() -> ScribevalSettings:
    """Load settings from environment."""
    return ScribevalSettings()
