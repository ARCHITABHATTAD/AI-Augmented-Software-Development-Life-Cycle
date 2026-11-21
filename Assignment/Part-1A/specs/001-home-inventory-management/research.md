# Research: Home Inventory and Stock Management

## Decisions

### Runtime and HTTP interface

- **Decision**: Use Python 3.12 and FastAPI, served locally with Uvicorn.
- **Rationale**: Python 3.12 is available in the project environment, and FastAPI is already
  installed there. FastAPI provides request validation and an OpenAPI interface while keeping
  endpoint tests runnable in process.
- **Alternatives considered**: A standard-library HTTP server would reduce dependencies but require
  custom request parsing, validation, and contract documentation. Flask would work but would need
  additional schema and OpenAPI choices.

### Persistence

- **Decision**: Use SQLite through Python's standard-library `sqlite3` module, with a configurable
  file path and one connection per request.
- **Rationale**: SQLite meets the persistence requirement without a separate service or ORM.
  Parameterized statements and database constraints provide a clear, testable persistence boundary.
- **Alternatives considered**: An ORM adds a dependency and abstraction not needed for this small
  single-entity service. An in-memory store does not survive restart.

### App and test isolation

- **Decision**: Expose an app factory accepting database path and settings; use temporary SQLite
  files for contract tests.
- **Rationale**: Each test can use isolated persistent state, and tests can verify restart behavior
  without relying on process-global state or external services.
- **Alternatives considered**: A single global app and shared database are simpler to launch but
  make tests order-dependent and harder to isolate.

### Numeric values and ordering

- **Decision**: Validate quantities and prices as finite, non-negative numeric values, persist
  numeric values in SQLite, and apply explicit stable ordering with identifier as the tie-breaker.
- **Rationale**: This preserves the spec's support for fractional quantities and deterministic sort
  behavior while keeping the data model small. Validation must reject NaN and infinity as invalid
  JSON-domain values.
- **Alternatives considered**: Whole-number quantities conflict with the clarification allowing
  fractions. Adding per-item units or a currency-conversion subsystem exceeds the single-household
  scope.

### Currency

- **Decision**: Use one ISO 4217 currency code for the running inventory, configured at startup and
  documented in the API contract; default it to INR for the local project context. Do not store a
  currency per item or perform conversion.
- **Rationale**: The clarification requires one consistent currency and the assignment context is
  local. A single setting keeps prices interpretable without introducing multi-currency behavior.
- **Alternatives considered**: A currency field on each item would permit mixed-currency records and
  require conversion or currency-aware sorting; leaving currency implicit would make price values
  ambiguous.

### Stock threshold

- **Decision**: Configure one non-negative threshold at startup, defaulting to 1, and expose
  low-stock inventory through a dedicated read endpoint.
- **Rationale**: This follows the clarification and allows deterministic low-stock tests without a
  mutable configuration API.
- **Alternatives considered**: A runtime threshold endpoint or per-item thresholds require
  additional state and behavior not requested by the spec.

### Testing and tooling

- **Decision**: Use pytest, FastAPI `TestClient`, HTTPX, and Ruff; record runtime and development
  dependencies in separate requirements files.
- **Rationale**: These tools are installed in the existing local environment and support focused,
  repeatable unit and HTTP contract testing.
- **Alternatives considered**: Adding a new test runner or external database is unnecessary for
  this project.

## Deferred to Implementation

- The exact application module entry point and local Uvicorn command are specified in
  `quickstart.md`.
- The generated OpenAPI contract is the authoritative reference for request/response field names,
  media types, and error response shape.
