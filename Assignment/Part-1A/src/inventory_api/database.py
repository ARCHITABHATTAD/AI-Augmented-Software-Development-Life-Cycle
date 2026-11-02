"""SQLite connection and schema lifecycle."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS inventory_items (
    id TEXT PRIMARY KEY COLLATE BINARY
        CHECK (length(trim(id)) > 0),
    name TEXT NOT NULL
        CHECK (length(trim(name)) > 0),
    category TEXT NOT NULL
        CHECK (length(trim(category)) > 0),
    quantity REAL NOT NULL
        CHECK (quantity >= 0 AND quantity <= 1.7976931348623157e308),
    unit_price REAL NOT NULL
        CHECK (unit_price >= 0 AND unit_price <= 1.7976931348623157e308),
    expiry_date TEXT
)
"""


@contextmanager
def connect(database_path: Path) -> Iterator[sqlite3.Connection]:
    """Yield a transaction-scoped SQLite connection and always close it."""
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path, timeout=5.0)
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize_database(database_path: Path) -> None:
    """Create the inventory schema if it does not already exist."""
    with connect(database_path) as connection:
        connection.execute(SCHEMA)
