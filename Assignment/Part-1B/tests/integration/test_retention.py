from datetime import UTC, datetime, timedelta

from src.domain.triage import TriageService
from src.persistence.database import SQLiteRepository
from src.providers.mock_provider import MockProvider


def test_30_day_deadline_deletes_record_and_prevents_retrieval(make_settings):
    settings = make_settings()
    repository = SQLiteRepository(settings.database_path, settings.reviewer_credentials)
    result = TriageService(MockProvider()).triage("Thank you for your help.")
    now = datetime.now(UTC)
    expired_id = repository.create_record(
        "Expired message", result, created_at=now - timedelta(days=30)
    )
    live_id = repository.create_record("Live message", result, created_at=now)

    report = repository.cleanup_expired(now=now)

    assert report.deleted_count == 1
    assert report.overdue_count == 1
    assert report.remaining_overdue_count == 0
    assert repository.get_record(expired_id, now=now) is None
    assert repository.record_exists(live_id)


def test_failed_cleanup_reports_error_for_retry(monkeypatch, tmp_path, caplog):
    from src.persistence import retention

    monkeypatch.setattr(
        retention,
        "SQLiteRepository",
        lambda _: (_ for _ in ()).throw(OSError("database unavailable")),
    )
    assert retention.cleanup(str(tmp_path / "unavailable.sqlite3")) == 1
    assert "retention_cleanup_failed" in caplog.text
