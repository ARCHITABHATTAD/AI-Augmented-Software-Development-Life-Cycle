from fastapi.testclient import TestClient

from src.api.app import create_app
from src.providers.base import ProviderUnavailable
from src.providers.mock_provider import MockProvider


class CountingProvider:
    def __init__(self):
        self.calls = 0

    def triage(self, message):
        self.calls += 1
        return MockProvider().triage(message)


class UnavailableProvider:
    def triage(self, message):
        raise ProviderUnavailable("test provider unavailable")


def test_empty_input_is_rejected_without_provider_call_or_persistence(make_settings):
    provider = CountingProvider()
    app = create_app(make_settings(), provider=provider)
    with TestClient(app) as client:
        response = client.post("/triage", json={"message": " \t "})
    assert response.status_code == 422
    assert provider.calls == 0
    assert app.state.repository.count_records() == 0


def test_valid_triage_is_persisted_with_exact_contract(make_settings):
    app = create_app(make_settings(), provider=MockProvider())
    with TestClient(app) as client:
        response = client.post(
            "/triage",
            json={"message": "The website displays an error on the support form."},
        )
    assert response.status_code == 200
    assert response.headers["X-Record-ID"]
    assert set(response.json()) == {
        "category",
        "priority",
        "sentiment",
        "department",
        "suggested_response",
        "rationale",
        "clarification_required",
        "clarification_question",
        "human_review_required",
    }
    assert app.state.repository.count_records() == 1


def test_malformed_provider_output_returns_safe_error_and_is_not_persisted(make_settings):
    app = create_app(make_settings(), provider=MockProvider(raw_response="not json"))
    with TestClient(app) as client:
        response = client.post("/triage", json={"message": "I was charged twice."})
    assert response.status_code == 503
    assert response.json() == {"detail": "The triage provider returned invalid output."}
    assert app.state.repository.count_records() == 0


def test_unavailable_provider_returns_safe_error(make_settings):
    app = create_app(make_settings(), provider=UnavailableProvider())
    with TestClient(app) as client:
        response = client.post("/triage", json={"message": "I need help with billing."})
    assert response.status_code == 503
    assert response.json() == {"detail": "The triage provider is unavailable."}
    assert app.state.repository.count_records() == 0


def test_web_console_is_served(make_settings):
    app = create_app(make_settings(), provider=MockProvider())
    with TestClient(app) as client:
        page = client.get("/")
        script = client.get("/static/app.js")
        styles = client.get("/static/styles.css")

    assert page.status_code == 200
    assert "Support Triage Console" in page.text
    assert script.status_code == 200
    assert "triageForm" in script.text
    assert styles.status_code == 200
