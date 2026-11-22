import pytest

from src.config import ReviewerCredential, Settings


@pytest.fixture
def make_settings(tmp_path):
    def factory(
        *,
        reviewer_credentials=None,
        semantic_base_url=None,
        semantic_model=None,
        semantic_api_key=None,
    ):
        return Settings(
            database_path=str(tmp_path / "test.sqlite3"),
            triage_provider="mock",
            ai_base_url=None,
            ai_model=None,
            ai_api_key=None,
            ai_timeout_seconds=2.0,
            ai_max_retries=0,
            reviewer_credentials=tuple(
                reviewer_credentials
                or (
                    ReviewerCredential(
                        "reviewer", "test-reviewer-token", "support-reviewer"
                    ),
                    ReviewerCredential("agent", "test-agent-token", "support-agent"),
                )
            ),
            semantic_base_url=semantic_base_url,
            semantic_model=semantic_model,
            semantic_api_key=semantic_api_key,
            semantic_timeout_seconds=2.0,
            semantic_rubric_version="1",
        )

    return factory
