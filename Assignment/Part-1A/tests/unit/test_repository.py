from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pytest

from inventory_api.database import initialize_database
from inventory_api.repository import (
    DuplicateItemError,
    ItemNotFoundError,
    create_item,
    delete_item,
    get_item,
    list_items,
    list_low_stock_items,
    update_item,
)


@pytest.fixture
def database_path(tmp_path: Path) -> Path:
    path = tmp_path / "inventory.sqlite3"
    initialize_database(path)
    return path


def make_item(item_id: str = "rice", **overrides: Any) -> dict[str, Any]:
    return {
        "id": item_id,
        "name": "Rice",
        "category": "Pantry",
        "quantity": 2.5,
        "unit_price": 120.0,
        "expiry_date": date(2027, 1, 31),
        **overrides,
    }


def test_create_and_get_item(database_path: Path) -> None:
    created = create_item(database_path, make_item())

    assert created == make_item()
    assert get_item(database_path, "rice") == make_item()


def test_duplicate_identifier_does_not_replace_item(database_path: Path) -> None:
    create_item(database_path, make_item())

    with pytest.raises(DuplicateItemError):
        create_item(database_path, make_item(name="Replacement"))

    assert get_item(database_path, "rice")["name"] == "Rice"


def test_update_replaces_mutable_fields_without_changing_id(database_path: Path) -> None:
    create_item(database_path, make_item())

    updated = update_item(
        database_path,
        "rice",
        {
            "name": "Basmati Rice",
            "category": "Grains",
            "quantity": 1.25,
            "unit_price": 135.5,
            "expiry_date": None,
        },
    )

    assert updated == {
        "id": "rice",
        "name": "Basmati Rice",
        "category": "Grains",
        "quantity": 1.25,
        "unit_price": 135.5,
        "expiry_date": None,
    }


def test_missing_item_operations_raise_not_found(database_path: Path) -> None:
    with pytest.raises(ItemNotFoundError):
        get_item(database_path, "missing")
    with pytest.raises(ItemNotFoundError):
        update_item(
            database_path,
            "missing",
            {
                "name": "Rice",
                "category": "Pantry",
                "quantity": 1,
                "unit_price": 1,
                "expiry_date": None,
            },
        )
    with pytest.raises(ItemNotFoundError):
        delete_item(database_path, "missing")


def test_delete_item(database_path: Path) -> None:
    create_item(database_path, make_item())

    delete_item(database_path, "rice")

    with pytest.raises(ItemNotFoundError):
        get_item(database_path, "rice")


def test_database_constraints_reject_negative_values(database_path: Path) -> None:
    import sqlite3

    from inventory_api.database import connect

    with pytest.raises(sqlite3.IntegrityError), connect(database_path) as connection:
        connection.execute(
            """
                INSERT INTO inventory_items
                    (id, name, category, quantity, unit_price, expiry_date)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
            ("bad", "Bad", "Pantry", -1, 1, None),
        )

    assert list_items(database_path) == []


def test_list_category_uses_casefold_and_exact_matching(database_path: Path) -> None:
    create_item(database_path, make_item("one", category="Épicerie"))
    create_item(database_path, make_item("two", category="Other"))

    assert [item["id"] for item in list_items(database_path, category="épicerie")] == ["one"]
    assert list_items(database_path, category="ép") == []


@pytest.mark.parametrize(
    ("sort_by", "order", "expected"),
    [
        ("quantity", "asc", ["a", "b", "c"]),
        ("quantity", "desc", ["c", "a", "b"]),
        ("unit_price", "asc", ["c", "a", "b"]),
        ("unit_price", "desc", ["a", "b", "c"]),
        ("expiry_date", "asc", ["c", "a", "b"]),
        ("expiry_date", "desc", ["a", "c", "b"]),
    ],
)
def test_list_sorting_has_stable_identifier_ties_and_null_last(
    database_path: Path, sort_by: str, order: str, expected: list[str]
) -> None:
    create_item(database_path, make_item("b", quantity=1, unit_price=10, expiry_date=None))
    create_item(
        database_path,
        make_item("a", quantity=1, unit_price=10, expiry_date=date(2027, 1, 2)),
    )
    create_item(
        database_path,
        make_item("c", quantity=2, unit_price=5, expiry_date=date(2027, 1, 1)),
    )

    assert [
        item["id"] for item in list_items(database_path, sort_by=sort_by, order=order)
    ] == expected


def test_list_items_rejects_unsupported_sort(database_path: Path) -> None:
    with pytest.raises(ValueError, match="Unsupported sort field"):
        list_items(database_path, sort_by="name")


def test_low_stock_is_strictly_below_threshold(database_path: Path) -> None:
    create_item(database_path, make_item("low", quantity=0.99))
    create_item(database_path, make_item("equal", quantity=1))

    assert [item["id"] for item in list_low_stock_items(database_path, 1)] == ["low"]
    assert list_low_stock_items(database_path, 0) == []
