---
description: "Dependency-aware implementation tasks for AI Customer Support Ticket Triage"
---

# Tasks: AI Customer Support Ticket Triage

**Input**: Design documents in `specs/001-ai-support-ticket-triage/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `quickstart.md`, and
`contracts/`

**Task format**: `[ID] [P?] [Story] Description (depends on ...; FR/SC traceability ...)`

- `[P]` marks work that can proceed in parallel without editing the same files or relying on
  unfinished work.
- `[US1]`, `[US2]`, and `[US3]` map to the specification's user stories. `[Shared]` is cross-cutting.
- Dependencies refer to task IDs; no dependency means the task can start when its phase is ready.
- Implementation, testing, evaluation, and evidence tasks are grouped separately.
- Checked tasks reflect implementation and verification performed. The final human review remains
  pending and is not represented as complete.

## Phase 1: Project setup and configuration

**Purpose**: Establish a reproducible Python 3.12 project and protect local configuration.

- [x] T001 [P] [Shared] Create the planned `src/`, `prompts/`, `tests/`, `evals/`, `.harness/`,
  and `evidence/` directory structure at the Part-1B project root (FR-012, FR-013, SC-003,
  SC-006).
- [x] T002 [P] [Shared] Add `requirements.txt` for the planned Python 3.12 runtime, FastAPI,
  Pydantic, `jsonschema`, pytest/httpx, and the chosen configurable-provider adapter; do not add
  unrelated dependencies (FR-013).
- [x] T003 [P] [Shared] Add `.env.example` containing variable names and clearly non-secret
  placeholder values for application-provider configuration, semantic-evaluator model/rubric
  configuration, and local authentication secrets; include no real credentials (FR-015, FR-013,
  SC-007).
- [x] T004 [P] [Shared] Add `.gitignore` entries for virtual environments, Python/test caches,
  local SQLite databases, `.env`, and temporary generated outputs; do not ignore required
  `evidence/` deliverables (FR-015).

## Phase 2: Domain models, enums, and JSON output contract

**Purpose**: Implement types that exactly reflect the approved nine-field contract.

- [x] T005 [P] [US1] Implement typed category, priority, sentiment, and department enums plus the
  category-to-department mapping in `src/domain/enums.py` (FR-002–FR-005, SC-002, SC-004).
- [x] T006 [US1] Implement the Pydantic triage-result model in `src/domain/triage.py`, matching
  all nine fields, nullability, non-empty strings, and no-extra-fields behavior in
  `contracts/triage-result.schema.json` (FR-006, FR-007, FR-011, SC-001).
- [x] T007 [P] [US1] Add contract tests comparing the Pydantic model behavior with
  `contracts/triage-result.schema.json`, including department mapping and conditional
  clarification-question behavior, in `tests/contract/test_triage_contract.py` (FR-005, FR-007,
  SC-001, SC-002).

## Phase 3: Input validation and triage logic

**Purpose**: Implement message validation, classification decisions, clarification, and safety rules.

- [x] T008 [P] [US1] Implement incoming customer-message validation in
  `src/domain/input_validation.py`; empty or whitespace-only input must fail before provider calls
  or persistence (depends on T001; FR-001, SC-002).
- [x] T009 [US1] Implement core triage orchestration in `src/domain/triage.py` using allowed
  labels, risk/time-sensitivity priority criteria, sentiment evidence, and the department mapping
  (FR-002–FR-006, FR-011, SC-002, SC-004).
- [x] T010 [US1] Implement dominant-issue selection and focused clarification when multiple
  issues cannot be routed confidently; preserve best-supported labels (FR-002, FR-008, SC-002).
- [x] T011 [US2] Implement security-sensitive handling and prohibited-action guardrails in
  `src/domain/triage.py`: flag exposed secrets, suspected compromise/fraud for human review, never
  repeat exposed secrets, and never perform or claim a transaction/account modification
  (depends on T010; FR-009, FR-010, SC-002, SC-005).

## Phase 4: AI provider interface, mock provider, and configured provider

**Purpose**: Separate deterministic triage development from real application-provider calls.

- [x] T012 [P] [US1] Define the application-provider protocol and typed failure boundary in
  `src/providers/base.py` (FR-006, FR-007, FR-013).
- [x] T013 [P] [US1] Implement deterministic `MockProvider` fixtures in
  `src/providers/mock_provider.py` for offline development and repeatable tests, including a mode
  that injects an exact raw provider response from an evaluation fixture and bypasses real model
  calls; do not use it to generate semantic-evaluator scores (FR-013, FR-014).
- [x] T014 [US1] Implement the configurable real application-provider adapter in
  `src/providers/configured_provider.py`, reading credentials only from environment configuration
  and enforcing timeouts and bounded retries (FR-006, FR-007, FR-013).

## Phase 5: Prompt design and output parsing

**Purpose**: Constrain model instructions and reject malformed or unsafe provider responses.

- [x] T015 [US1] Write `prompts/triage.txt` covering labels, priority evidence, dominant issue,
  clarification rules, rationale/response quality, JSON-only output, and safety guardrails; also
  write `prompts/semantic-evaluation.txt` implementing the fixed `spec.md` rubric for response
  quality, rationale quality, and safety/non-misleading content, with 1–5 scores and a brief reason
  for each dimension (depends on T009, T011; FR-002–FR-011, FR-013–FR-014, SC-005).
- [x] T016 [US1] Implement provider-output parsing in `src/domain/validation.py` with independent
  Pydantic and JSON Schema validation; reject surrounding prose, malformed JSON, missing/extra
  fields, and inconsistent conditional fields (depends on T006, T008; FR-007, FR-013, SC-001).
- [x] T017 [US1] Integrate prompt, provider, and both validation modules
  (`src/domain/input_validation.py` for incoming messages and `src/domain/validation.py` for model
  output) in the triage service; unavailable providers or malformed model output must produce safe
  explicit errors and no invented/persisted result (`src/domain/triage.py`; depends on T008–T016;
  FR-001, FR-007, FR-008, FR-013).

## Phase 6: Authentication and reviewer authorization

**Purpose**: Restrict retained-record access to authenticated support reviewers.

- [x] T018 [US2] Implement local session or bearer-token authentication and role resolution in
  `src/api/auth.py`, using environment-provided secrets and the authorized `support-reviewer` role
  (FR-015, SC-007).
- [x] T019 [US2] Implement reusable authorization enforcement for every retained-record read in
  `src/api/auth.py`; deny unauthenticated principals and authenticated users without the reviewer
  role (FR-015, SC-007).

## Phase 7: SQLite persistence and 30-day retention

**Purpose**: Persist records only for the approved audit/quality window and enforce expiration.

- [x] T020 [US2] Implement SQLite schema and repository operations for retained messages/results,
  UTC creation timestamps, and 30-day expiration in `src/persistence/database.py` (FR-015, SC-007).
- [x] T021 [US2] Implement `python -m src.persistence.retention --cleanup-expired` as an
  independently schedulable cleanup command in `src/persistence/retention.py`; delete records at
  or past `delete_after`, and document an external host scheduler running it at least hourly
  independently of the API process. Keep startup cleanup as an additional safeguard. Log
  non-sensitive success/failure outcomes to process/host monitoring, return a failure exit status
  so the next scheduled run retries, and report overdue-record count and oldest deadline for
  detection. Prevent expired rows from being returned after their deadline (FR-015, SC-007).

## Phase 8: FastAPI endpoints and error handling

**Purpose**: Expose the triage and authorized retained-record workflows.

- [x] T022 [US1] Implement `POST /triage` in `src/api/routes.py`; reject blank input before
  provider invocation and persistence, return exactly the validated JSON result, and retain valid
  outputs as specified (FR-001, FR-007, FR-015, SC-001).
- [x] T023 [US2] Implement retained-record read endpoint(s) in `src/api/routes.py`, enforcing
  authentication and reviewer-role checks on each access and hiding expired records (FR-015,
  SC-007; depends on T019–T022).
- [x] T024 [US1] Add centralized safe error mapping in `src/api/app.py` for invalid input,
  unavailable provider, malformed provider output, and internal failures; do not expose secrets,
  stack traces, or success-shaped fallback results (FR-001, FR-007, FR-010).

## Phase 9: Unit, contract, integration, and security tests

**Purpose**: Verify implementation behavior independently of evaluation-dataset scoring.

- [x] T025 [P] [US1] Add unit tests for empty and whitespace-only input, including assertions that
  no provider call or record creation occurs, in `tests/unit/test_input_validation.py`
  (FR-001, SC-002).
- [x] T026 [P] [US1] Add tests for malformed JSON, prose-wrapped output, missing/extra fields,
  invalid enum values, and provider-unavailable errors in
  `tests/contract/test_provider_output.py` (FR-007, FR-013, SC-001).
- [x] T027 [P] [US1] Add triage tests for each category, priority boundary, sentiment, and
  category-to-department mapping in `tests/unit/test_triage.py` (FR-002–FR-005, SC-002, SC-004).
- [x] T028 [P] [US1] Add explicit multiple-issue, contradictory-evidence, and focused-clarification
  tests in `tests/behavioral/test_multiple_issues.py` (FR-002, FR-008, SC-002).
- [x] T029 [P] [US2] Add security-sensitive tests for exposed credentials, suspected compromise,
  and suspected fraud; assert human-review flags and no secret repetition in
  `tests/behavioral/test_security_sensitive.py` (FR-009, SC-002, SC-005).
- [x] T030 [P] [US2] Add prohibited-action tests for transaction and account-modification requests;
  assert no execution or completion claim in `tests/behavioral/test_prohibited_actions.py`
  (FR-010, SC-002, SC-005).
- [x] T031 [P] [US2] Add integration tests for authenticated reviewer success, unauthenticated
  denial, and authenticated unauthorized-role denial in
  `tests/security/test_reviewer_access.py` (depends on T018, T019, T020, T023; FR-015, SC-007).
- [x] T032 [P] [US2] Add integration tests proving 30-day expiration deletes a record and prevents
  retrieval; verify cleanup failures are observable, overdue records are reported, and cleanup can
  be retried after recovery in `tests/integration/test_retention.py` (FR-015, SC-007).
- [x] T033 [US1] Add FastAPI integration tests for valid triage JSON, 422 empty input, 503 provider
  failure, and no persistence on rejected or malformed requests in
  `tests/integration/test_triage_api.py` (FR-001, FR-007, FR-015, SC-001, SC-002).
- [x] T034 [Shared] Run and document the targeted unit, contract, integration, and security suites;
  fix only failures in scope and retain regression tests (`README.md` test instructions)
  (FR-001–FR-016, SC-001–SC-008).

## Phase 10: Evaluation dataset with at least 15 meaningful cases

**Purpose**: Establish reviewed and traceable test cases before running aggregate evaluation.

- [x] T035 [US3] Create `evals/dataset.json` with at least 15 meaningful cases spanning all
  categories and priority levels, normal/boundary/ambiguous/underspecified/missing-information/
  malformed-provider-output/security-sensitive/adversarial cases, multiple issues, and prohibited
  actions. Represent malformed provider output with a raw-response fixture sent through the
  deterministic fake provider, bypassing a real model call; keep the customer message valid
  (FR-012, SC-003).
- [x] T036 [US3] Add stable case IDs, reviewed expected labels/assertions, semantic expectations,
  expected outcome, and FR/SC plus behavioral-invariant traceability IDs to every case. Require a
  deterministic raw provider-output fixture for malformed-provider-output cases (optional for
  others), and validate those cases use valid customer messages in
  `tests/evaluation/test_dataset.py` (FR-012, FR-016, SC-003, SC-008).

## Phase 11: Structural/schema evaluator

**Purpose**: Independently verify raw output shape and schema conformance.

- [x] T037 [US3] Implement `src/evaluation/structural_evaluator.py` to parse output, enforce
  exactly the nine required fields and Draft 2020-12 schema, and report case-level failure codes.
  Execute malformed-provider-output fixtures through the deterministic fake provider, record the
  raw response's structural failure, and mark the case PASS only when the application safely
  rejects it without persisting a result; accepting invalid output or returning a success-shaped
  fallback fails the case and layer (FR-007, FR-013, SC-001, SC-006, SC-008).

## Phase 12: Behavioural invariant evaluator

**Purpose**: Deterministically check safety and behavioral properties without model scoring.

- [x] T038 [US3] Implement `src/evaluation/behavioral_evaluator.py` for allowed values, department
  mapping, clarification conditions, security flags/secret non-repetition, prohibited actions,
  dominant-issue handling, invalid-input rejection, and retention/access properties (FR-001–FR-002,
  FR-005, FR-007–FR-010, FR-015, SC-001, SC-002, SC-007).

## Phase 13: Classification agreement evaluator

**Purpose**: Report independent agreement for each classification field.

- [x] T039 [US3] Implement `src/evaluation/classification_evaluator.py` comparing category,
  priority, sentiment, and department with reviewed expectations; report each per-field rate and
  case mismatch (FR-013, SC-004, SC-006, SC-008).

## Phase 14: Fixed-rubric semantic evaluator

**Purpose**: Score semantic quality with the configured model, never a mock or fabricated result.

- [x] T040 [US3] Implement `src/evaluation/semantic_evaluator.py` using the fixed rubric and
  separately configured, pinned semantic-evaluator model; score response, rationale, and safety
  dimensions from 1–5 with a brief reason for each (depends on T003, T015, T035, T036; FR-013,
  FR-014, SC-005, SC-006).
- [x] T041 [US3] Validate evaluator model identity/configuration and returned scores/reasons;
  report missing credentials or unavailable evaluator as `BLOCKED` and invalid/incomplete
  evaluator output as `INCOMPLETE`, never substituting scores (`src/evaluation/semantic_evaluator.py`,
  `tests/evaluation/test_semantic_status.py`) (FR-013, FR-014, SC-005, SC-006).

## Phase 15: Single evaluation runner and aggregate outcomes

**Purpose**: Run all mandatory layers and system-level verification with an honest aggregate status.

- [x] T042 [US3] Implement `src/evaluation/runner.py` to execute structural, behavioral,
  classification, semantic, and separate system-level authentication/retention verification
  groups and report each independently (FR-013, FR-015, FR-016, SC-006–SC-008).
- [x] T043 [US3] Implement aggregate metrics and the predeclared thresholds: schema 100%,
  behavioral 100%, each classification field at least 80%, each semantic dimension mean at least
  4.0/5, and no security-sensitive/prohibited-action safety score below 4/5
  (`src/evaluation/report.py`) (FR-013, FR-014, SC-001–SC-006).
- [x] T044 [P] [US3] Add runner/report tests for `PASS`, `FAIL`, `BLOCKED`, and `INCOMPLETE`;
  verify overall `PASS` is impossible unless every mandatory layer and system-level check
  completes and meets thresholds (`tests/evaluation/test_runner_status.py`) (FR-013, FR-016,
  SC-001, SC-002, SC-006, SC-008).

## Phase 16: Harness-driven repair and re-evaluation

**Purpose**: Use meaningful evaluation evidence to drive narrow fixes without weakening acceptance.

- [x] T045 [US3] Implement failure handoff records with case ID, input, generated output, failed
  requirement/invariant/check, expected/actual behavior, and suggested repair area; preserve hard
  cases and thresholds on every rerun (`src/evaluation/report.py`,
  `.harness/run-evaluation.py`) (FR-013, FR-016, SC-006, SC-008).

## Phase 17: Evidence generation and human acceptance

**Purpose**: Record real evaluation runs and human review without fabricated results.

- [x] T046 [US3] Implement evidence output to `evidence/initial-generation/`,
  `evidence/final-generation/`, `evidence/eval-results.json`, and
  `evidence/harness-log.md`; record provider/evaluator model and rubric configuration without
  secrets, all layer/system statuses, thresholds, failures, repairs, and reruns (FR-013, FR-016,
  SC-006, SC-008).
- [ ] T047 [US3] Add final review gate requiring actual evidence and a human `ACCEPT` or `REJECT`
  decision with limitations and risks; never generate placeholder success results or mark an
  incomplete run as passed (`evidence/harness-log.md`) (FR-013, FR-016, SC-006, SC-008).

## Phase 18: README and final submission verification

**Purpose**: Make the assignment reproducible and verify required deliverables.

- [x] T048 [P] [Shared] Write root `README.md` with Python 3.12 installation, environment
  configuration, application startup, test commands, evaluation commands, and the distinction
  between mock application provider and fixed semantic evaluator; document hourly retention
  scheduler setup, monitoring, outage limitations, and recovery (depends on T002–T004, T034,
  T042; FR-013, FR-015).
- [x] T049 [Shared] Verify required files/directories, clean secret handling, test commands,
  dataset traceability, all declared thresholds, evidence status semantics, and submission layout;
  document unresolved limitations without claiming unrun features passed (FR-001–FR-016,
  SC-001–SC-008).

## Dependencies and execution order

- **Phase 1** has no external prerequisites. T001 creates the project structure; T002–T004 depend
  on T001 and can proceed independently once it is complete.
- **Phase 2** depends on the project structure. T005 precedes T006; T007 depends on the model and
  schema contract.
- **Phases 3–8** form the application path: domain work depends on Phase 2; providers and prompts
  depend on the domain contract; auth and persistence precede protected endpoints; API errors
  depend on provider and validation boundaries.
- **Phase 9 tests** depend on their corresponding implementation interfaces and should be run as
  soon as each focused component is ready.
- **Phase 10** dataset definition depends on the approved requirement and invariant contract.
- **Phases 11–14** depend on the dataset/traceability structure and implement separate evaluation
  layers; the semantic evaluator additionally requires its own configured model and rubric.
- **Phase 15** depends on all four layers and the reviewer/retention system checks. T044 depends
  on the runner and status logic.
- **Phase 16** depends on runner failure output; **Phase 17** depends on completed actual runs;
  **Phase 18** is final documentation and verification.
- `[P]` tasks may be parallelized only when their listed prerequisites are complete and work does
  not conflict in shared files.

### Task-level prerequisite map

- T001: none. T002–T004: T001.
- T005: T001. T006: T005. T007: T006.
- T008: T001. T009: T005, T006, T008. T010: T009. T011: T010.
- T012: T002. T013: T012. T014: T003, T012.
- T015: T009, T011. T016: T006, T008. T017: T008–T016.
- T018: T003. T019: T018.
- T020: T001, T006. T021: T020.
- T022: T008, T009, T017, T020, T021. T023: T019–T022. T024: T022–T023.
- T025: T008. T026: T016–T017. T027: T009. T028: T010.
- T029–T030: T011. T031: T018, T019, T020, T023. T032: T020–T021.
- T033: T022–T024. T034: T025–T033.
- T035: T001. T036: T005, T011, T035.
- T037: T006, T013, T016, T035–T036. T038: T011, T035–T036.
- T039: T005, T035–T036. T040: T003, T015, T035–T036. T041: T040.
- T042: T031–T032, T037–T041. T043: T042. T044: T042–T043.
- T045: T042, T044. T046: T042, T045. T047: T046.
- T048: T002–T004, T034, T042. T049: T034, T036, T047–T048.

## Requirement traceability index

| Requirement/success criteria | Primary tasks |
|---|---|
| FR-001 | T008, T025, T033, T038 |
| FR-002–FR-005 | T005, T009–T010, T027–T028, T038 |
| FR-006–FR-007 | T006, T015–T017, T026–T027, T037–T038 |
| FR-008 | T010, T028, T038 |
| FR-009–FR-010 | T011, T029–T030, T038 |
| FR-011 | T006, T009, T027, T040 |
| FR-012 | T035–T036 |
| FR-013–FR-014 | T037–T044 |
| FR-015 | T003, T018–T024, T031–T032, T038, T042 |
| FR-016 | T036, T039, T042, T045–T047 |
| SC-001–SC-002 | T007, T016, T025–T030, T037–T038, T043–T044 |
| SC-003–SC-004 | T027, T035–T036, T039, T043 |
| SC-005 | T029–T030, T040–T043 |
| SC-006–SC-008 | T036–T047 |

## Notes

- Keep all tasks small and verifiable; tests and evidence remain distinct from implementation tasks.
- Do not remove difficult evaluation cases, relax thresholds, or weaken security/behavioral rules
  to obtain a passing report.
- `PASS`, `FAIL`, `BLOCKED`, and `INCOMPLETE` must preserve the distinctions in `plan.md`.
- Do not create evaluation results until the harness has actually run; no task in this plan
  represents completed work.
