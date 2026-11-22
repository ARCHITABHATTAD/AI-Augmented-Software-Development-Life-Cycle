import pytest

from src.domain.input_validation import InputValidationError, validate_customer_message
from src.domain.triage import EmptyCustomerMessage, TriageService
from src.providers.mock_provider import MockProvider


@pytest.mark.parametrize("message", ["", " ", " \t\r\n "])
def test_empty_and_whitespace_messages_are_rejected(message):
    with pytest.raises(InputValidationError):
        validate_customer_message(message)


def test_validation_preserves_original_nonblank_message():
    message = "  My package is late.  "
    assert validate_customer_message(message) == message


def test_blank_input_fails_before_provider_call():
    provider = MockProvider()
    with pytest.raises(EmptyCustomerMessage):
        TriageService(provider).triage("   ")
    assert provider.last_response is None
