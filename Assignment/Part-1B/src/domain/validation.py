from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError
from pydantic import ValidationError

if TYPE_CHECKING:
    from src.domain.triage import TriageResult


class ProviderOutputError(ValueError):
    def __init__(self, message: str, *, raw_output: str | None = None):
        super().__init__(message)
        self.raw_output = raw_output


SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "specs"
    / "001-ai-support-ticket-triage"
    / "contracts"
    / "triage-result.schema.json"
)


def load_schema() -> dict[str, Any]:
    with SCHEMA_PATH.open(encoding="utf-8") as schema_file:
        return json.load(schema_file)


def validate_provider_output(raw_output: str) -> TriageResult:
    from src.domain.triage import TriageResult

    if not isinstance(raw_output, str):
        raise ProviderOutputError("Provider output must be JSON text.")
    try:
        parsed = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        raise ProviderOutputError("Provider returned malformed JSON.", raw_output=raw_output) from exc
    if not isinstance(parsed, dict):
        raise ProviderOutputError("Provider output must be a JSON object.", raw_output=raw_output)
    try:
        Draft202012Validator(load_schema()).validate(parsed)
        return TriageResult.model_validate(parsed)
    except (JsonSchemaValidationError, ValidationError, OSError, json.JSONDecodeError) as exc:
        raise ProviderOutputError(
            "Provider output does not match the triage result contract.",
            raw_output=raw_output,
        ) from exc
