from src.domain.triage import TriageService
from src.providers.mock_provider import MockProvider


def test_dominant_payment_issue_is_selected_without_incompatible_routing():
    result = TriageService(MockProvider()).triage(
        "My package is late, and the payment charged twice."
    )
    assert result.category.value == "PAYMENT"
    assert result.department.value == "PAYMENT_SUPPORT"
    assert result.clarification_required is False


def test_underspecified_message_asks_a_focused_question():
    result = TriageService(MockProvider()).triage("Please help.")
    assert result.clarification_required is True
    assert result.clarification_question
    assert "describe" in result.clarification_question.lower()


def test_clear_message_does_not_ask_for_unnecessary_information():
    result = TriageService(MockProvider()).triage(
        "The app crashes every time I open it."
    )
    assert result.clarification_required is False
    assert result.clarification_question is None
