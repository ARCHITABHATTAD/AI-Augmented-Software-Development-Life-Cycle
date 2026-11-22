from src.domain.enums import CATEGORY_TO_DEPARTMENT
from src.domain.triage import TriageService
from src.providers.mock_provider import MockProvider


def triage(message):
    return TriageService(MockProvider()).triage(message)


def test_mock_classifies_supported_categories_and_department_mapping():
    examples = {
        "I was charged twice for this subscription.": "PAYMENT",
        "My delivery package is late.": "DELIVERY",
        "I cannot sign in to my account.": "ACCOUNT",
        "The website shows an error.": "TECHNICAL",
        "Thank you for the support hours.": "GENERAL",
    }
    for message, expected_category in examples.items():
        result = triage(message)
        assert result.category.value == expected_category
        assert result.department == CATEGORY_TO_DEPARTMENT[result.category]


def test_priority_and_sentiment_use_message_evidence():
    result = triage("An urgent app outage blocked essential work and is frustrating.")
    assert result.priority.value == "HIGH"
    assert result.sentiment.value == "NEGATIVE"


def test_result_has_exactly_nine_fields():
    result = triage("Thank you for your help.")
    assert len(result.model_dump()) == 9
