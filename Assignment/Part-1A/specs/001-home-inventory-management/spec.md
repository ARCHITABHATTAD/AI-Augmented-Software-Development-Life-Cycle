# Feature Specification: Home Inventory and Stock Management

**Feature Branch**: `001-home-inventory-management`

**Created**: 2026-11-02

**Status**: Draft

**Input**: User description: "Build a Home Inventory and Stock Management System that enables users to maintain household inventory records. Users must be able to add, retrieve, update and delete items, search inventory by category, sort items by quantity, price or expiry date, and identify items whose quantity falls below a configurable stock threshold. Each item must have a unique identifier, name, category, quantity, unit price and optional expiry date. The application must validate all inputs, reject negative quantities and prices, prevent duplicate identifiers, and return meaningful HTTP status codes for invalid or unavailable records. Inventory records must persist in SQLite and remain available after application restart. The system must expose REST API endpoints and have measurable acceptance criteria that can be independently verified using automated tests. The implementation must be small, locally executable and suitable for deterministic unit and contract testing."

## Clarifications

### Session 2026-11-02

- Q: How should the system interpret and present an item's unit price? → A: One configured currency applies to every item; currency is documented and consistent across the inventory.
- Q: When should the stock threshold be configurable? → A: Set one system-wide threshold at application startup, defaulting to 1 when unspecified.
- Q: Can an item's quantity be fractional, or must it be a whole-number count? → A: Allow non-negative fractional quantities without a separate unit-of-measure field.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Maintain Household Items (Priority: P1)

A household user records items and their quantities and prices, retrieves an item by its identifier,
updates its details as the household changes, and removes items that are no longer tracked.

**Why this priority**: Reliable inventory records are the core value of the system; all other
inventory workflows depend on them.

**Independent Test**: Create an item, retrieve it, update its details, and delete it through the
REST interface; verify each response and the resulting item state independently.

**Acceptance Scenarios**:

1. **Given** an item identifier not already in use and valid required details, **When** the user
   creates the item, **Then** the system stores it and returns HTTP 201.
2. **Given** a stored item, **When** the user retrieves it by identifier, **Then** the system
   returns HTTP 200 and all stored details.
3. **Given** a stored item and valid replacement details, **When** the user updates it,
   **Then** the system returns HTTP 200, stores the changes, and keeps the identifier unchanged.
4. **Given** a stored item, **When** the user deletes it, **Then** the system removes it and returns
   HTTP 204.
5. **Given** an identifier that is not stored, **When** the user retrieves, updates, or deletes it,
   **Then** the system returns HTTP 404 with a meaningful error response.
6. **Given** an identifier already in use, **When** the user attempts to create another item with
   it, **Then** the system returns HTTP 409 and does not change the existing item.
7. **Given** invalid item details, including a negative quantity or unit price, **When** the user
   creates or updates an item, **Then** the system returns HTTP 400 with a meaningful validation
   message and makes no partial change.

---

### User Story 2 - Find and Review Stock (Priority: P2)

A household user filters items by category, sorts the inventory to compare quantities, prices, or
expiry dates, and identifies items below the configured stock level.

**Why this priority**: Finding and prioritizing existing items makes the recorded inventory useful
for replenishment and expiry review.

**Independent Test**: Populate items with varied categories, quantities, prices, and expiry dates;
verify category results, each supported sort order, and low-stock results against known expected
sets and ordering.

**Acceptance Scenarios**:

1. **Given** items in multiple categories, **When** the user searches for a category,
   **Then** the system returns only matching items and returns HTTP 200 with an empty list if there
   are no matches.
2. **Given** items with different quantities, prices, or expiry dates, **When** the user requests
   sorting by one of those fields in ascending or descending order, **Then** the system returns
   items in that order.
3. **Given** an item with no expiry date and items with expiry dates, **When** the user sorts by
   expiry date, **Then** items without an expiry date appear after dated items in either direction.
4. **Given** a configured stock threshold, **When** the user requests low-stock items,
   **Then** the system returns exactly the items whose quantities are strictly below the threshold.

---

### User Story 3 - Keep Inventory Across Restarts (Priority: P3)

A household user expects saved inventory to remain available after the local application is stopped
and started again.

**Why this priority**: Inventory is only dependable if saved records survive routine application
restarts.

**Independent Test**: Save an item, stop and restart the application using the same local data
store, then retrieve the item and compare all of its fields.

**Acceptance Scenarios**:

1. **Given** an item has been successfully saved, **When** the application is restarted,
   **Then** retrieving that item returns the same identifier, name, category, quantity, unit price,
   and optional expiry date.
2. **Given** the application has no matching stored items, **When** it is restarted,
   **Then** inventory remains empty rather than being populated with example or stale records.

### Edge Cases

- A request with a missing or blank identifier, name, or category is rejected with HTTP 400.
- A request with a non-numeric quantity or unit price, or an invalid expiry date, is rejected with
  HTTP 400 and does not create or partially update an item.
- Zero quantity and zero unit price are valid non-negative values.
- A category search with no matching items returns HTTP 200 and an empty collection, not HTTP 404.
- An unsupported sort field or direction is rejected with HTTP 400.
- Items tied on the selected sort value are ordered by identifier ascending, so results are
  deterministic.
- An item without an expiry date sorts after items with dates, whether expiry sorting is ascending
  or descending.
- A threshold of zero is valid and returns no items when quantities are non-negative; an invalid or
  negative threshold is rejected rather than silently replaced.
- A PUT request replaces all mutable item fields. If `expiry_date` is omitted or explicitly set to
  `null`, the stored expiry date is cleared.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow users to create, retrieve, update, and delete inventory items
  through REST endpoints.
- **FR-002**: Each item MUST have a unique, non-empty identifier, a non-empty name, a non-empty
  category, a non-negative numeric quantity that may be fractional, a non-negative numeric unit
  price in the inventory's one configured currency, and an optional valid expiry date. The currency
  MUST be documented in the API contract.
- **FR-003**: The system MUST reject duplicate identifiers with HTTP 409 and MUST NOT overwrite or
  modify the existing item.
- **FR-004**: The system MUST reject missing, malformed, or invalid item input with HTTP 400 and a
  meaningful message identifying the input error. A rejected update MUST leave the stored item
  unchanged.
- **FR-005**: The system MUST return HTTP 404 with a meaningful message when a requested item
  identifier does not exist.
- **FR-006**: The system MUST return HTTP 201 for a successful creation, HTTP 200 for successful
  retrieval and update, and HTTP 204 for successful deletion.
- **FR-007**: An item's identifier MUST remain unchanged when its other details are updated. An
  update request MUST identify the item being changed and MUST NOT change a different item.
- **FR-008**: The system MUST allow users to search inventory by category, matching category text
  without regard to letter case. A search with no matches MUST return HTTP 200 and an empty
  collection.
- **FR-009**: The system MUST allow users to sort inventory by quantity, unit price, or expiry
  date, in ascending or descending order. Items tied on the selected value MUST be ordered by
  identifier ascending. Items without an expiry date MUST appear after dated items in either
  expiry-date sort direction.
- **FR-010**: The system MUST provide a way to identify items whose quantity is strictly below a
  configurable, system-wide stock threshold. The threshold MUST be set at application startup,
  default to 1 when not specified, and reject negative or invalid values.
- **FR-011**: The system MUST persist inventory records in SQLite and make successfully saved
  records available after an application restart.
- **FR-012**: The system MUST provide clear HTTP status codes and useful error responses for invalid
  input, duplicate identifiers, and unavailable records, without returning success-shaped results
  for failures.
- **FR-013**: The system MUST be locally executable and support deterministic automated unit and
  REST contract tests without dependence on external services.

### Key Entities

- **Inventory Item**: A household record identified by a unique identifier and containing a name,
  category, quantity, unit price in the inventory's configured currency, and optional expiry date.
- **Stock Threshold**: A configurable system-wide quantity level used to determine which inventory
  items are considered low stock.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of automated acceptance cases for item creation, retrieval, update, and deletion
  produce the expected HTTP status and final inventory state.
- **SC-002**: 100% of automated invalid-input and duplicate-identifier cases are rejected with the
  specified status, useful error information, and no unintended data change.
- **SC-003**: For every supported category search and sort field/direction, 100% of results in the
  acceptance tests match the expected items and deterministic ordering.
- **SC-004**: 100% of low-stock acceptance cases return exactly those items with quantity below the
  configured threshold, including the default threshold behavior.
- **SC-005**: Every item in the persistence acceptance test retains all submitted fields after an
  application restart.
- **SC-006**: The unit and REST contract acceptance suite passes repeatedly using local test data
  without calling external services.

## Assumptions

- The initial release is for one household using a locally run service; user accounts, access
  control, shared households, and remote hosting are out of scope.
- Item identifiers are supplied by the user, are unique as entered, and are treated as
  case-sensitive.
- Quantities and unit prices may be numeric values, including fractional quantities; zero is valid.
  Quantities do not require a separate unit-of-measure field.
  One configured currency applies to all unit prices and is documented in the API contract.
- Category search is an exact category match that ignores letter case; it is not a partial-text
  search.
- There is one system-wide stock threshold set at application startup, with a default of 1 in the
  quantity's unit unless configured otherwise; changing it while the service is running is out of
  scope.
- Updates replace item details other than the identifier. An omitted or explicitly null expiry
  date clears the stored date.
- This specification retains REST and SQLite as explicit user requirements; other implementation
  choices remain open to planning.
