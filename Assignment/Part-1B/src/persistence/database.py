from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from src.config import ReviewerCredential
from src.domain.triage import TriageResult
from src.persistence.reviewers import token_digest

LOGGER = logging.getLogger(__name__)
RETENTION_PERIOD = timedelta(days=30)


@dataclass(frozen=True)
class CleanupReport:
    deleted_count: int
    overdue_count: int
    oldest_overdue_delete_after: str | None
    remaining_overdue_count: int


class SQLiteRepository:
    def __init__(
        self, database_path: str, reviewer_credentials: tuple[ReviewerCredential, ...] = ()
    ):
        self.database_path = database_path
        if database_path != ":memory:":
            Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        self.initialize()
        self.provision_reviewers(reviewer_credentials)

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.database_path, timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        try:
            yield connection
            connection.commit()
        except sqlite3.Error:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS retained_records (
                    record_id TEXT PRIMARY KEY,
                    message TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    delete_after TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS retained_records_delete_after
                    ON retained_records(delete_after);
                CREATE TABLE IF NOT EXISTS reviewers (
                    username TEXT PRIMARY KEY,
                    token_hash TEXT NOT NULL UNIQUE,
                    role TEXT NOT NULL
                );
                """
            )

    def provision_reviewers(
        self, credentials: tuple[ReviewerCredential, ...]
    ) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM reviewers")
            connection.executemany(
                "INSERT INTO reviewers (username, token_hash, role) VALUES (?, ?, ?)",
                [
                    (item.username, token_digest(item.token), item.role)
                    for item in credentials
                ],
            )

    def resolve_reviewer(self, token: str) -> dict[str, str] | None:
        digest = token_digest(token)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT username, role FROM reviewers WHERE token_hash = ?", (digest,)
            ).fetchone()
        if row is None:
            return None
        return {"username": row["username"], "role": row["role"]}

    def record_exists(self, record_id: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM retained_records WHERE record_id = ?", (record_id,)
            ).fetchone()
        return row is not None

    def count_records(self) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM retained_records"
            ).fetchone()
        return int(row["count"])

    def create_record(
        self, message: str, result: TriageResult, *, created_at: datetime | None = None
    ) -> str:
        created = _as_utc(created_at or datetime.now(UTC))
        deleted = created + RETENTION_PERIOD
        record_id = str(uuid.uuid4())
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO retained_records
                    (record_id, message, result_json, created_at, delete_after)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    record_id,
                    message,
                    result.model_dump_json(),
                    _iso(created),
                    _iso(deleted),
                ),
            )
        return record_id

    def get_record(
        self, record_id: str, *, now: datetime | None = None
    ) -> dict[str, Any] | None:
        current = _as_utc(now or datetime.now(UTC))
        self.cleanup_expired(now=current)
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT record_id, message, result_json, created_at, delete_after
                FROM retained_records
                WHERE record_id = ? AND delete_after > ?
                """,
                (record_id, _iso(current)),
            ).fetchone()
        if row is None:
            return None
        return {
            "record_id": row["record_id"],
            "message": row["message"],
            "triage_result": json.loads(row["result_json"]),
            "created_at": row["created_at"],
            "delete_after": row["delete_after"],
        }

    def cleanup_expired(self, *, now: datetime | None = None) -> CleanupReport:
        current_iso = _iso(_as_utc(now or datetime.now(UTC)))
        with self._connect() as connection:
            overdue = connection.execute(
                """
                SELECT COUNT(*) AS count, MIN(delete_after) AS oldest
                FROM retained_records WHERE delete_after <= ?
                """,
                (current_iso,),
            ).fetchone()
            overdue_count = int(overdue["count"])
            oldest = overdue["oldest"]
            cursor = connection.execute(
                "DELETE FROM retained_records WHERE delete_after <= ?", (current_iso,)
            )
            deleted_count = cursor.rowcount
            remaining = connection.execute(
                "SELECT COUNT(*) AS count FROM retained_records WHERE delete_after <= ?",
                (current_iso,),
            ).fetchone()
            remaining_count = int(remaining["count"])

        report = CleanupReport(
            deleted_count=deleted_count,
            overdue_count=overdue_count,
            oldest_overdue_delete_after=oldest,
            remaining_overdue_count=remaining_count,
        )
        if overdue_count:
            LOGGER.warning(
                "retention_cleanup_overdue overdue_count=%s oldest_delete_after=%s "
                "deleted_count=%s remaining_overdue_count=%s",
                overdue_count,
                oldest,
                deleted_count,
                remaining_count,
            )
        else:
            LOGGER.info("retention_cleanup_completed deleted_count=0 overdue_count=0")
        return report


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("Timestamps must be timezone-aware.")
    return value.astimezone(UTC)


def _iso(value: datetime) -> str:
    return _as_utc(value).isoformat(timespec="microseconds")
