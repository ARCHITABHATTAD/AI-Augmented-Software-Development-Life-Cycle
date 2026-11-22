from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field

from src.domain.enums import (
    CATEGORY_TO_DEPARTMENT,
    Category,
    Department,
    Priority,
    Sentiment,
)
from src.domain.input_validation import validate_customer_message
from src.domain.validation import validate_provider_output
from src.providers.base import AIProvider


class TriageResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: Category
    priority: Priority
    sentiment: Sentiment
    department: Department
    suggested_response: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    clarification_required: bool
    clarification_question: str | None
    human_review_required: bool


class TriageError(Exception):
    pass


class EmptyCustomerMessage(TriageError):
    pass


class InvalidCustomerMessage(TriageError):
    pass


class TriageService:
    def __init__(self, provider: AIProvider):
        self.provider = provider

    def triage(self, message: str) -> TriageResult:
        try:
            validate_customer_message(message)
        except ValueError as exc:
            if isinstance(message, str):
                raise EmptyCustomerMessage("Message must not be empty or whitespace-only.") from exc
            raise InvalidCustomerMessage("Message must be a string.") from exc

        raw_output = self.provider.triage(message)
        result = validate_provider_output(raw_output)
        return apply_deterministic_safety_rules(message, result)


_SECRET_VALUE = re.compile(
    r"(?i)\b(?:password|passcode|verification code|one[- ]time code|api key|access token)"
    r"\s*(?:is|:)\s*[\"']?([^\s,;\"']+)"
)
_SECURITY_SIGNALS = (
    "password",
    "passcode",
    "verification code",
    "one-time code",
    "api key",
    "access token",
    "card number",
    "cvv",
    "security code",
    "account compromise",
    "unauthorized login",
    "unknown login",
    "fraud",
    "stolen",
)
_PROHIBITED_ACTION_SIGNALS = (
    "refund me",
    "send money",
    "transfer money",
    "pay this",
    "change my email",
    "change my password",
    "modify my account",
    "update my account",
    "cancel my account",
    "make a payment",
)
_COMPLETION_CLAIM = re.compile(
    r"(?i)\b(?:i|we)\s+(?:have\s+)?(?:completed|processed|refunded|transferred|changed|updated|"
    r"cancelled|canceled|paid)\b"
)


def is_security_sensitive(message: str) -> bool:
    lowered = message.lower()
    return any(signal in lowered for signal in _SECURITY_SIGNALS)


def is_prohibited_action_request(message: str) -> bool:
    lowered = message.lower()
    return any(signal in lowered for signal in _PROHIBITED_ACTION_SIGNALS)


def apply_deterministic_safety_rules(
    message: str, result: TriageResult
) -> TriageResult:
    updates: dict[str, object] = {}
    if result.department != CATEGORY_TO_DEPARTMENT[result.category]:
        updates["department"] = CATEGORY_TO_DEPARTMENT[result.category]

    sensitive = is_security_sensitive(message)
    prohibited = is_prohibited_action_request(message)
    if sensitive or prohibited:
        updates["human_review_required"] = True

    secret_values = {match.group(1) for match in _SECRET_VALUE.finditer(message)}
    output_repeats_secret = any(
        secret
        and secret.lower() in f"{result.suggested_response} {result.rationale}".lower()
        for secret in secret_values
    )
    if sensitive and result.suggested_response:
        updates["suggested_response"] = (
            "Please do not share passwords or verification codes. A support specialist should "
            "review this message."
        )
    if output_repeats_secret:
        updates["rationale"] = (
            "The message contains sensitive information, so human review is required. "
            "Sensitive values are omitted."
        )
    if prohibited and _COMPLETION_CLAIM.search(result.suggested_response):
        updates["suggested_response"] = (
            "I cannot perform financial transactions or account changes. A support specialist "
            "can review your request."
        )

    if not updates:
        return result
    return result.model_copy(update=updates)


def department_for(category: Category) -> Department:
    return CATEGORY_TO_DEPARTMENT[category]
