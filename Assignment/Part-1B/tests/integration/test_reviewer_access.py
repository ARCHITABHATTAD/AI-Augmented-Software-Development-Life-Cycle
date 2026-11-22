from fastapi.testclient import TestClient

from src.api.app import create_app
from src.domain.triage import TriageService
from src.providers.mock_provider import MockProvider


def test_reviewer_access_authentication_and_role(make_settings):
    app = create_app(make_settings(), provider=MockProvider())
    repository = app.state.repository
    result = TriageService(MockProvider()).triage("Thank you for your help.")
    record_id = repository.create_record("Thank you for your help.", result)

    with TestClient(app) as client:
        reviewer = client.get(
            f"/retained/{record_id}",
            headers={"Authorization": "Bearer test-reviewer-token"},
        )
        unauthenticated = client.get(f"/retained/{record_id}")
        invalid_token = client.get(
            f"/retained/{record_id}",
            headers={"Authorization": "Bearer invalid-token"},
        )
        unauthorized_role = client.get(
            f"/retained/{record_id}",
            headers={"Authorization": "Bearer test-agent-token"},
        )
        openapi = client.get("/openapi.json").json()

    assert reviewer.status_code == 200
    assert reviewer.json()["record_id"] == record_id
    assert unauthenticated.status_code == 401
    assert invalid_token.status_code == 401
    assert unauthorized_role.status_code == 403
    assert openapi["paths"]["/retained/{record_id}"]["get"]["security"] == [
        {"reviewerAuth": []}
    ]
    assert openapi["components"]["securitySchemes"]["reviewerAuth"] == {
        "type": "http",
        "scheme": "bearer",
        "description": "Local access token for a configured support reviewer.",
    }
