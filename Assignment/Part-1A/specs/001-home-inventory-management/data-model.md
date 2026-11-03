# Data Model: Home Inventory and Stock Management

## Inventory Item

Represents one household item tracked in the inventory.

| Field | Type | Required | Rules |
|---|---|---:|---|
| `id` | string | Yes | User-supplied, non-empty, unique, case-sensitive; immutable after creation. |
| `name` | string | Yes | Non-empty after trimming whitespace. |
| `category` | string | Yes | Non-empty after trimming whitespace. |
| `quantity` | number | Yes | Finite and greater than or equal to zero; fractional values are allowed. |
| `unit_price` | number | Yes | Finite and greater than or equal to zero; interpreted in the configured inventory currency. |
| `expiry_date` | date or null | No | Optional valid calendar date; may be cleared on update. |

The configured inventory currency is shared by all item prices; it is not an item-level attribute.
The API contract documents the configured currency. The API does not perform currency conversion.

### Persistence and identity

- SQLite stores each item in one `inventory_items` table.
- `id` is the primary key; the database enforces uniqueness in addition to application validation.
- SQLite constraints reject null required values and negative quantities or prices.
- A request with an identifier already present fails without changing the existing row.
- Delete removes the item; there are no soft-delete states or item-to-item relationships.

### Validation and state transitions

- Create validates all fields before inserting; only a successful insert creates an item.
- Update replaces all mutable fields as a single operation; an omitted or explicit null
  `expiry_date` clears the stored date. Invalid data or an unknown identifier does not partially
  modify inventory.
- The identifier in the update path is authoritative and cannot be changed in the body.
- Retrieve and list operations do not mutate inventory.
- Delete transitions an existing item to absent; attempting to delete an absent item returns 404.

## Stock Threshold

One application-wide setting determines which items are low stock.

| Field | Type | Rules |
|---|---|---|
| `threshold` | number | Configured at startup; finite, non-negative; defaults to `1`. |

An item is low stock exactly when `quantity < threshold`. The threshold is configuration, not a
persisted entity or per-item field.

## Deterministic Ordering

- Quantity and unit-price sorts use numeric values.
- Expiry-date sorts put dated items before items with no expiry date in both directions.
- Items equal on the requested sort value use `id` ascending as a stable tie-breaker.
- Category matching is exact and case-insensitive.
