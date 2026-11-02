"""SQLite persistence operations for inventory items."""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path
from typing import Any

from inventory_api.database import connect


class DuplicateItemError(Exception):
    """Raised when an item identifier already exists."""


class ItemNotFoundError(Exception):
    """Raised when an item identifier does not exist."""


def _item_from_row(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    if item["expiry_date"] is not None:
        item["expiry_date"] = date.fromisoformat(item["expiry_date"])
    return item


def create_item(database_path: Path, item: dict[str, Any]) -> dict[str, Any]:
    try:
        with connect(database_path) as connection:
            connection.execute(
                """
                INSERT INTO inventory_items
                    (id, name, category, quantity, unit_price, expiry_date)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    item["id"],
                    item["name"],
                    item["category"],
                    item["quantity"],
                    item["unit_price"],
                    item["expiry_date"].isoformat() if item["expiry_date"] else None,
                ),
            )
    except sqlite3.IntegrityError as exc:
        if "UNIQUE constraint failed: inventory_items.id" in str(exc):
            raise DuplicateItemError(item["id"]) from exc
        raise
    return get_item(database_path, item["id"])


def get_item(database_path: Path, item_id: str) -> dict[str, Any]:
    with connect(database_path) as connection:
        row = connection.execute(
            "SELECT id, name, category, quantity, unit_price, expiry_date "
            "FROM inventory_items WHERE id = ?",
            (item_id,),
        ).fetchone()
    if row is None:
        raise ItemNotFoundError(item_id)
    return _item_from_row(row)


def update_item(database_path: Path, item_id: str, fields: dict[str, Any]) -> dict[str, Any]:
    expiry_date = fields["expiry_date"]
    with connect(database_path) as connection:
        cursor = connection.execute(
            """
            UPDATE inventory_items
            SET name = ?, category = ?, quantity = ?, unit_price = ?, expiry_date = ?
            WHERE id = ?
            """,
            (
                fields["name"],
                fields["category"],
                fields["quantity"],
                fields["unit_price"],
                expiry_date.isoformat() if expiry_date else None,
                item_id,
            ),
        )
    if cursor.rowcount == 0:
        raise ItemNotFoundError(item_id)
    return get_item(database_path, item_id)


def delete_item(database_path: Path, item_id: str) -> None:
    with connect(database_path) as connection:
        cursor = connection.execute(
            "DELETE FROM inventory_items WHERE id = ?",
            (item_id,),
        )
    if cursor.rowcount == 0:
        raise ItemNotFoundError(item_id)


def _sort_items(
    items: list[dict[str, Any]], sort_by: str | None, order: str
) -> list[dict[str, Any]]:
    items.sort(key=lambda item: item["id"])
    if sort_by is None:
        return items
    if sort_by == "expiry_date":
        dated = [item for item in items if item["expiry_date"] is not None]
        undated = [item for item in items if item["expiry_date"] is None]
        dated.sort(key=lambda item: item["expiry_date"], reverse=order == "desc")
        return dated + undated
    if sort_by not in {"quantity", "unit_price"}:
        raise ValueError(f"Unsupported sort field: {sort_by}")
    items.sort(key=lambda item: item[sort_by], reverse=order == "desc")
    return items


def list_items(
    database_path: Path,
    category: str | None = None,
    sort_by: str | None = None,
    order: str = "asc",
) -> list[dict[str, Any]]:
    with connect(database_path) as connection:
        rows = connection.execute(
            "SELECT id, name, category, quantity, unit_price, expiry_date FROM inventory_items"
        ).fetchall()
    items = [_item_from_row(row) for row in rows]
    if category is not None:
        requested_category = category.strip().casefold()
        items = [item for item in items if item["category"].casefold() == requested_category]
    return _sort_items(items, sort_by, order)


def list_low_stock_items(database_path: Path, threshold: float) -> list[dict[str, Any]]:
    with connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT id, name, category, quantity, unit_price, expiry_date
            FROM inventory_items
            WHERE quantity < ?
            ORDER BY id COLLATE BINARY ASC
            """,
            (threshold,),
        ).fetchall()
    return [_item_from_row(row) for row in rows]
