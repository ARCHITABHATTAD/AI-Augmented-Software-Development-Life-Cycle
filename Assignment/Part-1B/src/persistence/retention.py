from __future__ import annotations

import argparse
import logging
import sqlite3
import sys

from src.config import Settings
from src.persistence.database import SQLiteRepository

LOGGER = logging.getLogger(__name__)


def cleanup(database_path: str) -> int:
    try:
        repository = SQLiteRepository(database_path)
        report = repository.cleanup_expired()
    except (OSError, sqlite3.Error) as exc:
        LOGGER.error("retention_cleanup_failed error_type=%s", type(exc).__name__)
        return 1
    if report.remaining_overdue_count:
        LOGGER.error(
            "retention_cleanup_incomplete remaining_overdue_count=%s "
            "oldest_delete_after=%s",
            report.remaining_overdue_count,
            report.oldest_overdue_delete_after,
        )
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Delete expired triage records.")
    parser.add_argument(
        "--cleanup-expired",
        action="store_true",
        help="delete records at or past their 30-day deadline",
    )
    arguments = parser.parse_args(argv)
    if not arguments.cleanup_expired:
        parser.error("--cleanup-expired is required.")
    settings = Settings.from_env()
    return cleanup(settings.database_path)


if __name__ == "__main__":
    sys.exit(main())
