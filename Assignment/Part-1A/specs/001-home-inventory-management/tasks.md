---
description: "Dependency-ordered implementation tasks for Home Inventory and Stock Management"
---

# Tasks: Home Inventory and Stock Management

**Input**: Design documents from `specs/001-home-inventory-management/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/openapi.yaml`

**Tests**: Included because the specification requires automated unit and REST contract tests.

**Organization**: Tasks are grouped by user story so each increment can be implemented and
validated independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Task can run in parallel with another task in its phase because it edits separate files
  and has no dependency on unfinished work.
- **[Story]**: User-story label (`US1`, `US2`, or `US3`) for story-phase tasks.
- Every task names the file or files to create or modify.

## Phase 1: Setup

**Purpose**: Create the Python service package, dependency metadata, and test/lint configuration.

- [X] T001 Create the `src/inventory_api/` package, `tests/unit/`, and `tests/contract/` directories with package initializers where needed.
- [X] T002 Define Python 3.12 project metadata, src-layout packaging, pytest discovery, Ruff settings, and runtime dependencies in `pyproject.toml` and `requirements.txt`.
- [X] T003 [P] List pytest, HTTPX, and Ruff development dependencies in `requirements-dev.txt`.

## Phase 2: Foundational

**Purpose**: Implement and verify shared configuration and persistent storage prerequisites before user-story work.

- [X] T004 Implement typed startup settings for `INVENTORY_DB_PATH`, `LOW_STOCK_THRESHOLD` (default `1`), and `INVENTORY_CURRENCY` (default `INR`) in `src/inventory_api/config.py`; reject invalid, negative, NaN, or infinite thresholds and currency values that do not match the three-letter ISO 4217 format.
- [X] T005 [P] Implement SQLite connection lifecycle and initialize the `inventory_items` table with an identifier primary key, required fields, optional expiry date, and database checks for non-negative quantity and unit price in `src/inventory_api/database.py`.
- [X] T006 [P] Test startup setting defaults and invalid threshold/currency inputs in `tests/unit/test_config.py`.
- [X] T007 Create the FastAPI app factory, settings injection, startup database initialization, and standard HTTP error response handling in `src/inventory_api/app.py`.

**Checkpoint**: Settings, isolated database initialization, application construction, and shared error handling are ready for story implementation.

## Phase 3: User Story 1 - Maintain Household Items (Priority: P1) 🎯 MVP

**Goal**: Create, retrieve, update, and delete inventory items with clear validation and HTTP responses.

**Independent Test**: Against a temporary SQLite database, create an item (201), retrieve and update it (200), delete it (204), and verify duplicate, invalid, and unknown-item cases return 409, 400, and 404 without unintended state changes.

### Tests for User Story 1

- [X] T008 [P] [US1] Add REST contract tests for create, retrieve, update, delete, duplicate identifiers, unknown identifiers, invalid fields, immutable identifiers, error payloads, and required status codes in `tests/contract/test_api.py`.

### Implementation for User Story 1

- [X] T009 [P] [US1] Define item create, update, and response schemas in `src/inventory_api/models.py`; require non-empty `id`, `name`, and `category`, finite non-negative numeric `quantity` and `unit_price`, and an optional valid `expiry_date`; include the configured ISO 4217 currency code in item responses.
- [X] T010 [P] [US1] Implement parameterized SQLite insert, lookup, update, and delete operations in `src/inventory_api/repository.py`; enforce a unique case-sensitive identifier and leave stored rows unchanged on invalid or failed updates.
- [X] T011 [US1] Implement `POST /items`, `GET /items/{item_id}`, `PUT /items/{item_id}`, and `DELETE /items/{item_id}` with the contract's 201, 200, 204, 400, 404, and 409 responses in `src/inventory_api/app.py`.
- [X] T012 [US1] Run the User Story 1 contract tests and correct any mismatch between `src/inventory_api/app.py`, `src/inventory_api/models.py`, `src/inventory_api/repository.py`, and `specs/001-home-inventory-management/contracts/openapi.yaml`.

**Checkpoint**: User Story 1 is independently usable and validated against a temporary persistent database.

## Phase 4: User Story 2 - Find and Review Stock (Priority: P2)

**Goal**: Search by category, sort inventory deterministically, and return items below the configured threshold.

**Independent Test**: Populate a known inventory and verify exact case-insensitive category matches, ascending and descending quantity/price/expiry ordering, identifier tie-breaks, null expiry placement, empty search results, low-stock results, and invalid query responses.

### Tests for User Story 2

- [X] T013 [P] [US2] Add REST contract tests for category filtering, empty matches, all sort fields and directions, deterministic tie-breaking, null expiry placement, invalid sort parameters, and low-stock threshold results in `tests/contract/test_api.py`.

### Implementation for User Story 2

- [X] T014 [US2] Extend inventory repository queries with exact case-insensitive category matching, allowlisted quantity/unit-price/expiry sorting, identifier-ascending tie-breaking, null-expiry-last behavior in either direction, and strict `quantity < threshold` filtering in `src/inventory_api/repository.py`.
- [X] T015 [US2] Implement `GET /items` category/sort query validation and `GET /items/low-stock` using the configured startup threshold in `src/inventory_api/app.py`; register static routes before `/{item_id}`, return HTTP 200 with an empty array when no items match, and HTTP 400 for unsupported sort fields or directions.
- [X] T016 [US2] Run the User Story 2 contract tests and correct any mismatch between `src/inventory_api/repository.py`, `src/inventory_api/app.py`, and `specs/001-home-inventory-management/contracts/openapi.yaml`.

**Checkpoint**: User Story 2 is independently testable using known item data and the configured threshold.

## Phase 5: User Story 3 - Keep Inventory Across Restarts (Priority: P3)

**Goal**: Preserve all successfully saved item fields when the service restarts with the same database path.

**Independent Test**: Create an item in a temporary SQLite file, construct a fresh application instance with that same file, and retrieve the item with all fields unchanged; also verify a fresh empty file yields an empty inventory.

### Tests for User Story 3

- [X] T017 [P] [US3] Add persistence tests that write an item, reopen the same SQLite file through a fresh app instance, verify every field and configured currency, and verify an empty database remains empty in `tests/contract/test_api.py`.

### Implementation for User Story 3

- [X] T018 [US3] Verify database initialization is idempotent and existing rows remain available across independent app lifecycles; fix persistence lifecycle issues in `src/inventory_api/database.py` and `src/inventory_api/app.py`.
- [X] T019 [US3] Run the User Story 3 restart tests and ensure test database paths remain isolated from the default local database in `tests/contract/test_api.py`.

**Checkpoint**: User Story 3 proves durable inventory behavior independently of server-process global state.

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Align runtime documentation, contract, and quality checks with the implemented behavior.

- [X] T020 [P] Align `specs/001-home-inventory-management/contracts/openapi.yaml` and generated FastAPI OpenAPI docs with implemented field names, currency response field, HTTP 400 validation responses, and all endpoint responses; remove misleading HTTP 422 responses.
- [X] T021 [P] Update `specs/001-home-inventory-management/quickstart.md` with the final install, configuration, local run, example request, restart, pytest, and Ruff commands.
- [X] T022 Run the complete test suite twice and Ruff checks across `tests/` and `src/`; resolve failures in the affected files.
- [X] T023 Verify each success criterion and user-story scenario in `specs/001-home-inventory-management/spec.md`; record any remaining gap in `specs/001-home-inventory-management/quickstart.md`.
- [X] T024 Review `specs/001-home-inventory-management/{spec.md,plan.md,data-model.md,contracts/openapi.yaml,quickstart.md}`, `src/inventory_api/{app.py,config.py,database.py,models.py,repository.py}`, and `tests/{contract/test_api.py,unit/test_config.py,unit/test_repository.py}` for requirement fit, correctness, security, and maintainability; verify material claims against project evidence and tests before release.

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No phase prerequisites.
- **Foundational (Phase 2)**: Depends on Setup; blocks all user-story implementation.
- **User Story 1 (Phase 3)**: Depends on Foundational; delivers the MVP.
- **User Story 2 (Phase 4)**: Depends on Foundational and the item storage/query capability from User Story 1.
- **User Story 3 (Phase 5)**: Depends on Foundational and the create/retrieve capability from User Story 1.
- **Polish (Phase 6)**: Depends on all user stories selected for delivery.
  - T024 follows implementation and test completion (T022 and T023).

### User Story Dependencies

- **US1 (P1)**: Starts after Foundational. No dependency on another user story.
- **US2 (P2)**: Uses the inventory entity and repository introduced by US1.
- **US3 (P3)**: Verifies the SQLite-backed create/retrieve flow introduced by US1.

### Within Each User Story

- Add contract tests before running the implementation verification task.
- Complete shared model/repository work before relying on its endpoints.
- Keep each story's implementation, tests, and verification together before calling the story complete.
- Tasks marked `[P]` edit separate files and can proceed independently once their phase prerequisites are met.

## Parallel Opportunities

- **Setup**: T003 can run alongside T001/T002 because it edits only `requirements-dev.txt`.
- **Foundational**: T005 and T006 can run in parallel after the package structure exists; T004 and T005 edit separate modules.
- **US1**: T008, T009, and T010 can be developed concurrently against the checked-in API contract; T011 depends on the schemas and repository; T012 runs after implementation.
- **US2**: T013 can be authored against the API contract while T014 is implemented; T015 depends on T014; T016 validates both.
- **US3**: T017 defines the restart acceptance test before T018's lifecycle verification.
- **Across stories**: US2 and US3 both depend on US1's foundational inventory API and are not independent of US1 in this plan.
- **Polish**: T024 is a final review after test and acceptance verification.

## Parallel Example: User Story 1

```text
After Phase 2 and the P1 interface is agreed:
Task: T008 - Add REST contract tests in tests/contract/test_api.py
Task: T009 - Define item schemas in src/inventory_api/models.py
Task: T010 - Implement SQLite CRUD in src/inventory_api/repository.py

Then complete T011 (routes) and T012 (contract verification).
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 setup.
2. Complete Phase 2 shared configuration and SQLite foundation.
3. Implement and independently test Phase 3 CRUD and validation.
4. Stop and verify the P1 acceptance scenarios before starting optional increments.

### Incremental Delivery

1. Add Phase 4 category search, sorting, and low-stock queries.
2. Add Phase 5 restart durability verification.
3. Complete Phase 6 contract/documentation alignment, full quality checks, and AI-assisted output review.

Each story is accepted only when its independent test criteria pass against an isolated local database.
