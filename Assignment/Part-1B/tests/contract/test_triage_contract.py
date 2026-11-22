import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from src.domain.triage import TriageResult
from src.domain.validation import (
    SCHEMA_PATH,
    ProviderOutputError,
    validate_provider_output,
)


def valid_result():
    return {
        "category": "PAYMENT",
        "priority": "MEDIUM",
        "sentiment": "NEGATIVE",
        "department": "PAYMENT_SUPPORT",
        "suggested_response": "A support agent can review the payment issue.",
        "rationale": "The message reports a payment issue.",
        "clarification_required": False,
        "clarification_question": None,
        "human_review_required": False,
    }


def test_pydantic_and_json_schema_accept_exact_contract():
    payload = valid_result()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(payload)
    parsed = TriageResult.model_validate(payload)
    assert parsed.model_dump(mode="json") == payload


@pytest.mark.parametrize(
    "change",
    [
        {"department": "GENERAL_SUPPORT"},
        {"clarification_required": True},
        {"priority": "URGENT"},
        {"unexpected": True},
    ],
)
def test_contract_rejects_invalid_values_and_conditionals(change):
    payload = valid_result()
    payload.update(change)
    with pytest.raises((ValidationError, ProviderOutputError)):
        validate_provider_output(json.dumps(payload))


def test_contract_schema_is_draft_2020_12():
    assert Path(SCHEMA_PATH).is_file()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema["$schema"].endswith("2020-12/schema")
