from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from inventory_api.app import create_app
from inventory_api.config import Settings


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    settings = Settings(
        database_path=tmp_path / "inventory.sqlite3",
        low_stock_threshold=1,
        currency="INR",
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def valid_item(**overrides: Any) -> dict[str, Any]:
    return {
        "id": "pantry-rice",
        "name": "Rice",
        "category": "Pantry",
        "quantity": 2.5,
        "unit_price": 120.0,
        "expiry_date": "2027-01-31",
        **overrides,
    }


def test_create_and_retrieve_item(client: TestClient) -> None:
    created = client.post("/items", json=valid_item())

    assert created.status_code == 201
    assert created.headers["location"].endswith("/items/pantry-rice")
    assert created.json() == {
        **valid_item(),
        "currency": "INR",
    }

    retrieved = client.get("/items/pantry-rice")
    assert retrieved.status_code == 200
    assert retrieved.json() == created.json()


def test_update_replaces_mutable_fields_and_omitted_expiry_is_cleared(
    client: TestClient,
) -> None:
    client.post("/items", json=valid_item())
    updated = client.put(
        "/items/pantry-rice",
        json={
            "name": "Basmati Rice",
            "category": "Grains",
            "quantity": 1.25,
            "unit_price": 135.5,
        },
    )

    assert updated.status_code == 200
    assert updated.json() == {
        "id": "pantry-rice",
        "name": "Basmati Rice",
        "category": "Grains",
        "quantity": 1.25,
        "unit_price": 135.5,
        "expiry_date": None,
        "currency": "INR",
    }


def test_explicit_null_expiry_clears_date(client: TestClient) -> None:
    client.post("/items", json=valid_item())
    update = {
        "name": "Rice",
        "category": "Pantry",
        "quantity": 2,
        "unit_price": 120,
        "expiry_date": None,
    }

    response = client.put("/items/pantry-rice", json=update)

    assert response.status_code == 200
    assert response.json()["expiry_date"] is None


def test_delete_item_returns_empty_204_and_then_not_found(client: TestClient) -> None:
    client.post("/items", json=valid_item())

    deleted = client.delete("/items/pantry-rice")

    assert deleted.status_code == 204
    assert deleted.content == b""
    missing = client.get("/items/pantry-rice")
    assert missing.status_code == 404
    assert isinstance(missing.json()["detail"], str)


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/items/missing"),
        ("delete", "/items/missing"),
    ],
)
def test_unknown_item_operations_return_404(client: TestClient, method: str, path: str) -> None:
    response = client.request(method.upper(), path, json={} if method == "put" else None)

    assert response.status_code == 404
    assert isinstance(response.json()["detail"], str)
    assert response.json()["detail"]


def test_update_unknown_item_returns_404(client: TestClient) -> None:
    response = client.put(
        "/items/missing",
        json={
            "name": "Rice",
            "category": "Pantry",
            "quantity": 2,
            "unit_price": 10,
        },
    )

    assert response.status_code == 404
    assert isinstance(response.json()["detail"], str)


def test_duplicate_identifier_returns_conflict_without_overwriting(
    client: TestClient,
) -> None:
    client.post("/items", json=valid_item())

    duplicate = client.post("/items", json=valid_item(name="Replacement"))

    assert duplicate.status_code == 409
    assert client.get("/items/pantry-rice").json()["name"] == "Rice"


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "Rice", "category": "Pantry", "quantity": 1, "unit_price": 1},
        valid_item(name=" "),
        valid_item(category=" "),
        valid_item(quantity=-0.1),
        valid_item(unit_price=-0.1),
        valid_item(quantity="not-a-number"),
        valid_item(quantity="2.5"),
        valid_item(unit_price="12.5"),
        valid_item(expiry_date="2027-02-30"),
        valid_item(quantity="Infinity"),
        valid_item(unexpected="field"),
    ],
)
def test_invalid_create_returns_400_with_field_message(
    client: TestClient, payload: dict[str, Any]
) -> None:
    response = client.post("/items", json=payload)

    assert response.status_code == 400
    assert isinstance(response.json()["detail"], str)
    assert response.json()["detail"]
    assert client.get("/items/pantry-rice").status_code == 404


def test_invalid_update_returns_400_without_partial_change(client: TestClient) -> None:
    client.post("/items", json=valid_item())

    response = client.put(
        "/items/pantry-rice",
        json={
            "name": "Changed",
            "category": "Pantry",
            "quantity": -1,
            "unit_price": 10,
        },
    )

    assert response.status_code == 400
    stored = client.get("/items/pantry-rice").json()
    assert stored["name"] == "Rice"
    assert stored["quantity"] == 2.5


def test_numeric_string_update_returns_400_without_partial_change(client: TestClient) -> None:
    client.post("/items", json=valid_item())

    response = client.put(
        "/items/pantry-rice",
        json={
            "name": "Changed",
            "category": "Pantry",
            "quantity": "3",
            "unit_price": 10,
        },
    )

    assert response.status_code == 400
    stored = client.get("/items/pantry-rice").json()
    assert stored["name"] == "Rice"
    assert stored["quantity"] == 2.5


def test_update_cannot_change_identifier(client: TestClient) -> None:
    client.post("/items", json=valid_item())

    response = client.put(
        "/items/pantry-rice",
        json={
            "id": "different-id",
            "name": "Rice",
            "category": "Pantry",
            "quantity": 2,
            "unit_price": 10,
        },
    )

    assert response.status_code == 400
    assert client.get("/items/pantry-rice").status_code == 200
    assert client.get("/items/different-id").status_code == 404


def test_list_items_defaults_to_deterministic_identifier_order(client: TestClient) -> None:
    client.post("/items", json=valid_item(id="z-item"))
    client.post("/items", json=valid_item(id="a-item"))

    response = client.get("/items")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == ["a-item", "z-item"]


def test_category_search_is_exact_and_case_insensitive(client: TestClient) -> None:
    client.post("/items", json=valid_item(id="rice", category="Pantry"))
    client.post("/items", json=valid_item(id="soap", category="Household"))
    client.post("/items", json=valid_item(id="tea", category=" pantry "))

    response = client.get("/items", params={"category": "PANTRY"})

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == ["rice", "tea"]
    empty = client.get("/items", params={"category": "Missing"})
    assert empty.status_code == 200
    assert empty.json() == []


@pytest.mark.parametrize(
    ("sort_by", "order", "expected_ids"),
    [
        ("quantity", "asc", ["a-item", "b-item", "d-item", "c-item"]),
        ("quantity", "desc", ["c-item", "d-item", "a-item", "b-item"]),
        ("unit_price", "asc", ["d-item", "a-item", "b-item", "c-item"]),
        ("unit_price", "desc", ["b-item", "c-item", "a-item", "d-item"]),
        ("expiry_date", "asc", ["c-item", "a-item", "b-item", "d-item"]),
        ("expiry_date", "desc", ["a-item", "c-item", "b-item", "d-item"]),
    ],
)
def test_sorting_is_stable_and_keeps_missing_dates_last(
    client: TestClient, sort_by: str, order: str, expected_ids: list[str]
) -> None:
    client.post(
        "/items",
        json=valid_item(id="a-item", quantity=1, unit_price=10, expiry_date="2027-01-03"),
    )
    client.post(
        "/items",
        json=valid_item(id="b-item", quantity=1, unit_price=20, expiry_date=None),
    )
    client.post(
        "/items",
        json=valid_item(id="c-item", quantity=3, unit_price=20, expiry_date="2027-01-01"),
    )
    client.post(
        "/items",
        json=valid_item(id="d-item", quantity=2, unit_price=5, expiry_date=None),
    )

    response = client.get("/items", params={"sort_by": sort_by, "order": order})

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == expected_ids


@pytest.mark.parametrize(
    "params",
    [
        {"sort_by": "name"},
        {"order": "sideways"},
    ],
)
def test_invalid_sort_parameters_return_400(client: TestClient, params: dict[str, str]) -> None:
    response = client.get("/items", params=params)

    assert response.status_code == 400
    assert isinstance(response.json()["detail"], str)


def test_low_stock_endpoint_is_not_captured_by_item_id_route(client: TestClient) -> None:
    client.post("/items", json=valid_item(id="low", quantity=0.5))
    client.post("/items", json=valid_item(id="threshold", quantity=1))
    client.post("/items", json=valid_item(id="above", quantity=2))

    response = client.get("/items/low-stock")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == ["low"]


def test_low_stock_threshold_can_be_zero(tmp_path: Path) -> None:
    settings = Settings(
        database_path=tmp_path / "zero-threshold.sqlite3",
        low_stock_threshold=0,
        currency="INR",
    )
    with TestClient(create_app(settings)) as zero_threshold_client:
        zero_threshold_client.post("/items", json=valid_item(id="zero", quantity=0))
        assert zero_threshold_client.get("/items/low-stock").json() == []


def test_saved_items_survive_a_fresh_application_instance(tmp_path: Path) -> None:
    database_path = tmp_path / "restart.sqlite3"
    settings = Settings(database_path, low_stock_threshold=1, currency="INR")
    with TestClient(create_app(settings)) as first_client:
        created = first_client.post("/items", json=valid_item())
        assert created.status_code == 201
        expected = created.json()

    with TestClient(create_app(settings)) as restarted_client:
        retrieved = restarted_client.get("/items/pantry-rice")
        assert retrieved.status_code == 200
        assert retrieved.json() == expected



def test_fresh_database_stays_empty_after_restart(tmp_path: Path) -> None:
    settings = Settings(tmp_path / "empty.sqlite3", low_stock_threshold=1, currency="INR")
    with TestClient(create_app(settings)):
        pass

    with TestClient(create_app(settings)) as restarted_client:
        assert restarted_client.get("/items").json() == []


def test_openapi_documents_http_400_validation_contract(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()

    assert "400" in schema["paths"]["/items"]["post"]["responses"]
    assert "400" in schema["paths"]["/items"]["get"]["responses"]
    assert "400" in schema["paths"]["/items/{item_id}"]["put"]["responses"]
    assert all(
        "422" not in operation["responses"]
        for path_item in schema["paths"].values()
        for operation in path_item.values()
        if "responses" in operation
    )
