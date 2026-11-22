import json

from src.domain.triage import TriageService
from src.providers.mock_provider import MockProvider
from tests.contract.test_triage_contract import valid_result


def test_refund_request_is_not_claimed_as_completed():
    result = TriageService(MockProvider()).triage("Please refund me now.")
    assert result.human_review_required is True
    assert "cannot perform" in result.suggested_response.lower()


def test_unsafe_completion_claim_is_replaced():
    unsafe = valid_result()
    unsafe["suggested_response"] = "I have refunded your payment."
    result = TriageService(MockProvider(json.dumps(unsafe))).triage("Please refund me.")
    assert "have refunded" not in result.suggested_response.lower()
