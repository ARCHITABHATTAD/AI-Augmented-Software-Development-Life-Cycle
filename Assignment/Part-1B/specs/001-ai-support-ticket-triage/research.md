# Phase 0 Research

## Framework and language

**Decision**: Python 3.12 with FastAPI.

**Rationale**: FastAPI and Pydantic provide typed HTTP boundaries and testable JSON responses.
Python is available in the existing environment, and SQLite requires no extra service.

**Rejected alternatives**: Node.js or a distributed framework would add dependencies without
satisfying an assignment-scale requirement. A CLI-only design would not provide authenticated
reviewer access.

## AI provider architecture

**Decision**: A provider protocol with a deterministic mock and configurable real adapter.

**Rationale**: Unit tests and offline evaluation need deterministic behavior. Real-provider
evaluation remains possible when credentials/configuration exist. The provider name and API key
are not assumed.

**Configuration**: Environment variables supply provider type, model name, endpoint, timeout,
temperature, API key, and evaluator mode. No secrets are written to source or evidence.

## Structured output

**Decision**: Prompt for JSON, parse only JSON, validate Pydantic types, and independently validate
the Draft 2020-12 JSON Schema.

**Rationale**: The schema deterministically catches extra properties, enum violations,
conditional-field errors, and invalid types. Pydantic provides convenient in-process API types but
is not the only structural check.

## Authentication

**Decision**: Locally managed authenticated session or bearer access token carrying an explicit
`support-reviewer` role.

**Rationale**: This satisfies FR-015 and SC-007 while remaining suitable for the assignment.
External identity providers, customer identity systems, enterprise SSO, and customer-record
integration remain outside scope.

**Implementation consideration**: Use environment-configured signing/session secrets and never
persist bearer tokens in plaintext in evidence or logs.

## Persistence and deletion

**Decision**: SQLite with UTC `created_at` and `delete_after` fields.

**Rationale**: SQLite is simple, local, dependency-light, and sufficient for assignment-scale
retention. Expose `python -m src.persistence.retention --cleanup-expired` as an independent cleanup
process, scheduled by the host at least hourly. It deletes records when `delete_after` is reached,
records non-sensitive cleanup outcomes for monitoring, exits unsuccessfully on failure, and is
retried at the next scheduled run. Startup cleanup is an additional safeguard, and retained-record
access also prevents expired records from being returned. Since cleanup is independent of the API,
it can continue during an application outage if the scheduler and SQLite database are available.

**Operational dependency and recovery**: The host scheduler must run reliably and have access to
the configured SQLite database; this external scheduler is an operational dependency, not an
application-library dependency. Monitor failed attempts and overdue-record count/oldest deadline.
If the host, scheduler, or database is unavailable, deletion by the deadline cannot be guaranteed.
After recovery, run cleanup and resume the hourly schedule; startup cleanup is an additional
recovery safeguard. Do not claim unconditional deletion when the scheduler or host is unavailable.

**Rejected alternatives**: Indefinite retention, external database infrastructure, or relying only
on manual deletion.

## Evaluation design

**Decision**: Four independent result layers and one runner.

**Rationale**: Schema, behavioral, classification, and semantic quality test different properties.
Semantic scoring must not replace structural or deterministic checks.

**Threshold rule**: Thresholds are declared before evaluation and preserved during repair.
