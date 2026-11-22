import json

from src.domain.triage import TriageService
from src.providers.mock_provider import MockProvider
from tests.contract.test_triage_contract import valid_result


def test_security_sensitive_message_requires_human_review():
    result = TriageService(MockProvider()).triage(
        "I accidentally shared my password and need help securing my account."
    )
    assert result.human_review_required is True
    assert "password" in result.suggested_response.lower()


def test_provider_output_cannot_repeat_an_exposed_secret():
    secret = "fake-test-secret-not-real"
    unsafe = valid_result()
    unsafe["category"] = "ACCOUNT"
    unsafe["department"] = "ACCOUNT_SUPPORT"
    unsafe["suggested_response"] = f"We received your password {secret}."
    unsafe["rationale"] = f"The password is {secret}."
    result = TriageService(MockProvider(json.dumps(unsafe))).triage(
        f"My password is {secret}; please help secure my account."
    )
    assert secret not in result.suggested_response
    assert secret not in result.rationale
    assert result.human_review_required is True
