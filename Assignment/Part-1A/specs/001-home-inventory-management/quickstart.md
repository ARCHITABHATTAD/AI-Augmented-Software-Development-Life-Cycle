# Quickstart: Home Inventory and Stock Management

## Prerequisites

- Python 3.12
- A local virtual environment

## Install

From the Part-1A project root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Configure and run

The service reads the following optional environment variables:

| Variable | Default | Meaning |
|---|---|---|
| `INVENTORY_DB_PATH` | `data/inventory.sqlite3` | SQLite file path |
| `LOW_STOCK_THRESHOLD` | `1` | Non-negative quantity threshold set at startup |
| `INVENTORY_CURRENCY` | `INR` | ISO 4217 currency code used for all item prices |

Start the local server from the project root:

```powershell
$env:INVENTORY_DB_PATH = ".\data\inventory.sqlite3"
$env:LOW_STOCK_THRESHOLD = "1"
$env:INVENTORY_CURRENCY = "INR"
.\.venv\Scripts\python.exe -m uvicorn inventory_api.app:app --app-dir src --reload
```

The interactive API documentation is available at `http://127.0.0.1:8000/docs`.

## Verify the REST contract

Create an item:

```powershell
curl.exe -i -X POST http://127.0.0.1:8000/items `
  -H "Content-Type: application/json" `
  -d '{"id":"pantry-rice","name":"Rice","category":"Pantry","quantity":2.5,"unit_price":120.00,"expiry_date":null}'
```

Expected: HTTP 201 and a JSON item response identifying the configured currency.

Retrieve the item with `GET /items/pantry-rice` (HTTP 200), then list or sort it with
`GET /items?category=pantry&sort_by=quantity&order=asc`. Check low stock with `GET /items/low-stock`.
An unknown item returns HTTP 404; a duplicate identifier returns HTTP 409; a negative quantity
returns HTTP 400.

## Verify persistence across restart

1. Create an item and stop the server.
2. Restart it with the same `INVENTORY_DB_PATH`.
3. Retrieve the item and verify all fields and currency are unchanged.

## Run automated checks

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\ruff.exe check src tests
```

Contract tests use a temporary SQLite file and the in-process test client; they do not call
external services or modify the local inventory database.
