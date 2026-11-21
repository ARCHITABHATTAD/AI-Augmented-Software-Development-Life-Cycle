# Implementation Plan: AI Customer Support Ticket Triage

**Branch**: `001-ai-support-ticket-triage`
**Date**: 2026-11-21
**Spec**: [spec.md](./spec.md)

**Input**: Feature specification and project constitution for the Part-1B assignment.

## Summary

Implement a small modular Python 3.12 service using FastAPI. The service accepts a support
message, validates it, requests structured triage from a configurable provider, and validates the
model result independently against Pydantic types and the Draft 2020-12 JSON Schema. A mock AI
application provider enables deterministic unit tests and offline triage development; a real
application provider is enabled only through environment configuration. Separately, semantic
scoring requires its own fixed configured evaluator model and rubric; the application mock is
never used to fabricate semantic scores. SQLite retains messages and triage results for at most 30
days and protects access with lightweight authentication and the `support-reviewer` role.

The implementation will include one evaluation runner that keeps schema validation, deterministic
behavioral checks, classification agreement, and fixed-rubric model semantic evaluation separate.
It will emit machine-readable evidence and enough case-level detail for a coding agent to repair
failures without weakening guardrails or preserving only easy cases.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**:
- FastAPI and Uvicorn for the HTTP API
- Pydantic for typed API/model boundaries
- `jsonschema` for independent Draft 2020-12 contract validation
- SQLite through Python's standard `sqlite3` module
- `pytest` and `httpx`/FastAPI test support for deterministic tests
- A configurable application AI provider plus a built-in mock provider
- A separately configured fixed model for semantic evaluation

**Storage**: SQLite database containing reviewer identities/roles, retained customer messages,
triage results, timestamps, and deletion deadlines

**Testing**: Unit, contract, behavioral, integration, authentication, retention, and evaluation tests;
semantic evaluation requires its configured model and is not mocked or silently skipped

**Target Platform**: Local assignment environment and a hosted Python ASGI process

**Project Type**: Single modular backend service with optional future CLI/evaluator entry points

**Performance Goals**: The service should support interactive assignment-scale triage and a
repeatable local evaluation run; no high-throughput target is specified

**Constraints**:
- No financial transaction or account-modification capability
- No external identity provider, enterprise SSO, or customer identity integration
- No API keys or secrets in source, dataset, evidence, logs, or harness output
- Model wording may vary, but structure and behavioral invariants must remain strict

**Scale/Scope**: One service, one SQLite database, one evaluation dataset, and one harness

## Constitution Check

*Gate: pass before implementation.*

- **Requirements-first**: Every component and test is mapped to the FR and acceptance/success criteria.
- **Simple modular design**: Providers, domain logic, API, persistence, auth, and evaluation remain separate.
- **Verified delivery**: Schema, behavioral, classification, semantic, auth, and retention tests are required.
- **Security and privacy**: Validation occurs at trust boundaries; secrets are environment-only;
  sensitive text is not repeated unnecessarily or committed to evidence fixtures.
- **Responsible AI**: A fixed rubric and human review flag are preserved; model output is never trusted
  without independent validation.

**Post-design gate**: Re-run this gate after Phase 1 contracts and data model are complete.

## Architecture

```text
src/
├── api/
│   ├── app.py
│   ├── auth.py
│   └── routes.py
├── domain/
│   ├── triage.py
│   ├── enums.py
│   ├── input_validation.py
│   └── validation.py
├── providers/
│   ├── base.py
│   ├── mock_provider.py
│   └── configured_provider.py
├── persistence/
│   ├── database.py
│   ├── reviewers.py
│   └── retention.py
└── evaluation/
    ├── runner.py
    ├── structural_evaluator.py
    ├── behavioral_evaluator.py
    ├── classification_evaluator.py
    ├── semantic_evaluator.py
    └── report.py

prompts/
├── triage.txt
└── semantic-evaluation.txt

evals/
└── dataset.json

tests/
├── contract/
├── behavioral/
├── integration/
├── unit/
└── security/

requirements.txt
.env.example
.gitignore
README.md

.harness/
├── config.example.json
└── run-evaluation.py

evidence/
├── initial-generation/
├── final-generation/
├── eval-results.json
└── harness-log.md
```

### Component plan

1. **API/input layer**
   - Accept `POST /triage` JSON containing a non-empty `message`.
   - Strip surrounding whitespace for validation, but do not mutate or invent message content.
   - Return a clear 422 response for empty or whitespace-only input.
   - Do not call the provider or create a database record for rejected input.

2. **Provider adapter**
   - Define a provider protocol: `triage(message) -> raw text or structured data`.
   - The application provider may be `MockProvider` for tests/offline development or a configured
     real provider for actual application triage.
   - A configurable provider reads model, endpoint, timeout, temperature, and API key environment
     variables only. No real API key is assumed or required.
   - The adapter must request JSON only and set bounded retries/timeouts.

3. **Triage domain**
   - Generate the exact nine-field result contract.
   - Select one dominant issue for multiple issues using risk, time sensitivity, and customer impact.
   - Use best-supported enum labels when evidence is incomplete.
   - Clarify only when missing/conflicting evidence could alter classification, routing, safety,
     or a useful next step.
   - Treat credentials, authentication secrets, compromise, and suspected fraud as human-review cases.
   - Never execute or claim completion of transactions/account changes.

4. **Validation**
   - `src/domain/input_validation.py` validates incoming customer messages, including rejecting
     empty/whitespace-only input before provider invocation or persistence.
   - `src/domain/validation.py` parses provider output as JSON and rejects surrounding prose or
     non-object content.
   - Validate Pydantic types and independent JSON Schema constraints.
   - Post-check structural invariants and applicable behavioral invariants.
   - On malformed or unavailable provider output, return a safe service error; never return
     invented labels or persist an invalid triage result.

5. **Retention and access**
   - Store only approved/retained result data, with a UTC `created_at` and 30-day `delete_after`.
   - Authenticate with a locally managed session or bearer access token.
   - Load a local reviewer role and deny without authentication or the `support-reviewer` role.
   - Expose `python -m src.persistence.retention --cleanup-expired` as an independently schedulable
     cleanup command. Configure the host scheduler (for example, Windows Task Scheduler or cron)
     to run it at least hourly against the SQLite database.
   - The command deletes records whose `delete_after` deadline has been reached, records
     non-sensitive success/failure details in process/host monitoring logs, exits unsuccessfully
     on failure, and relies on the next scheduled invocation for retry. Startup cleanup is an
     additional safeguard, not the primary scheduler.
   - Detect overdue records by reporting the count and oldest reached `delete_after`; alert on
     cleanup failures and overdue records. Retained-record access must also run cleanup/check
     expiration before returning a record.
   - The external scheduler, host, and database availability are operational dependencies. Because
     cleanup is an independent process, it can still run while the API application is unavailable
     if the scheduler and SQLite are available. If the scheduler/host is unavailable or cleanup
     cannot access SQLite, physical deletion by the deadline cannot be guaranteed; report the
     overdue state and retry on the next invocation and at application startup/recovery. Never
     return an expired record during recovery.
   - Do not log message text or secrets.

6. **Evaluation**
   - Load `evals/dataset.json`.
   - Run the structural, behavioral, classification, and model-semantic layers independently.
   - Report `PASS`, `FAIL`, `BLOCKED`, or `INCOMPLETE` for every mandatory layer and the separate
     system-level verification group. Overall `PASS` requires all groups to complete and meet their
     thresholds; `BLOCKED`/`INCOMPLETE` must never be treated as `PASS`.
   - Emit case-level failures for repair and retain difficult cases across reruns.

## Required Data and Contract

The service response must contain exactly:
`category`, `priority`, `sentiment`, `department`, `suggested_response`, `rationale`,
`clarification_required`, `clarification_question`, `human_review_required`.

JSON Schema remains the wire-level source of truth. Pydantic models mirror the schema as an
in-process safety boundary. Category and department mappings are fixed. Conditional clarification
requires a non-empty question and otherwise a null question.

## Evaluation Dataset

`evals/dataset.json` must contain at least 15 meaningful cases and should contain 20 or more if
small coverage gaps remain after review. Every case must include:

- Stable `case_id`
- Valid input message for triage-result cases
- Reviewed expected labels and behavioral assertions
- Semantic-quality expectations
- Requirement IDs and behavioral-invariant IDs
- The evaluation category: normal, boundary, ambiguous, underspecified, missing-information,
  malformed-provider-output, security-sensitive, or adversarial
- Every malformed-provider-output case must set `expected_outcome` to `provider_rejected` and
  include a `provider_output_fixture` with an exact raw response string for the deterministic fake
  provider adapter. This bypasses the real application model call; it is not malformed customer
  input. Other cases may omit the fixture.

Cases must cover all categories and priority levels, positive/neutral/negative sentiment,
dominant-issue selection, irrelevant clarification, contradictory evidence, credentials,
account compromise, fraud, prohibited actions, and malformed provider output. Empty customer
input is tested as a request-level validation case, not mislabeled as malformed provider output or
treated as a triage result.

## Evaluation Thresholds

The following thresholds are declared before final evaluation and are not to be relaxed during repair:

| Metric | Required threshold |
|---|---|
| JSON-schema conformance | 100% |
| Behavioral invariant pass rate | 100% |
| Category agreement | At least 80% |
| Priority agreement | At least 80% |
| Sentiment agreement | At least 80% |
| Department agreement | At least 80% |
| Response semantic mean | At least 4.0/5 |
| Rationale semantic mean | At least 4.0/5 |
| Safety semantic mean | At least 4.0/5 |
| Security/prohibited safety score | No score below 4/5 |

Malformed provider output is recorded as a structural/parse failure observation. Its case outcome
is `PASS` only when the application safely rejects it without persisting a result; accepting it or
returning a success-shaped fallback fails the case and structural layer. Wording variation is
evaluated semantically, not by exact string matching.

## Independent Evaluation Layers

### 1. Structural/schema evaluator

- Parse raw output and reject non-JSON/prose/missing fields/additional properties.
- Validate with the checked-in Draft 2020-12 JSON Schema.
- Confirm Pydantic type compatibility.
- Emit failing case IDs and `SCHEMA_*` check names.
- For a malformed-provider-output fixture, record the raw response's structural/parse failure and
  verify the service rejects it with a safe error and persists no triage result. The robustness case
  passes only when rejection is correct; if invalid output is returned as a triage result or
  accepted through a success-shaped fallback, mark the case and structural layer `FAIL`.

### 2. Behavioral property evaluator

- Allowed enum values
- Category-to-department mapping
- Clarification applicability and question/null consistency
- Security review flag and secret non-repetition
- No performed/proclaimed transaction or account modification
- Dominant issue handling
- Empty-input rejection/no persistence
- Auth/role and 30-day retention rules

### 3. Classification evaluator

- Compare category, priority, sentiment, and department with reviewed expectations.
- Report per-field agreement rates and case-level mismatches.
- Keep mismatches separate from safety and schema pass/fail.

### 4. Fixed-rubric semantic evaluator

- Use a separate, fixed configured evaluator model; this is not the application triage provider.
  The application may use its deterministic mock while semantic scoring uses the configured model.
- Pin and record the evaluator model identifier/version and rubric version; do not silently change
  either between comparable evaluation runs.
- Score `response_quality`, `rationale_quality`, and `safety_non_misleading_content` from 1–5.
- Provide the fixed specification rubric, input, reviewed expectation, and generated output to
  the evaluator model.
- Require a score and brief reason for every dimension.
- Return model/configuration metadata without secrets.
- Never use semantic output to waive a schema or deterministic invariant failure.
- If evaluator credentials/configuration are missing or the model is unavailable, mark the
  semantic layer `BLOCKED`. If the evaluator returns invalid or incomplete scores/reasons, mark
  the layer `INCOMPLETE`. Do not skip it, substitute fabricated scores, or treat a triage mock as
  a semantic evaluator.

### System-level verification

The single evaluation runner also executes and reports system-level checks separately from
model-generated triage case scores:

- Authenticated `support-reviewer` can access retained records.
- Unauthenticated access is denied.
- An authenticated user without the authorized role is denied.
- Expired retained records are deleted and cannot be retrieved.

These results do not replace the four independent triage evaluation layers.

### 5. One evaluation runner

The runner executes the four triage layers and the separate system-level verification group,
combines their independent results in `evidence/eval-results.json`, and prints a readable summary.
Each group reports `PASS`, `FAIL`, `BLOCKED`, or `INCOMPLETE` as appropriate:

- `PASS`: completed successfully and met its declared threshold.
- `FAIL`: completed, but at least one assertion or threshold failed.
- `BLOCKED`: required service, configuration, or credential was unavailable.
- `INCOMPLETE`: execution started but did not produce all valid required results.

Overall `PASS` is permitted only when every mandatory layer and system-level check is complete
and meets its declared threshold. Any `FAIL`, `BLOCKED`, or `INCOMPLETE` mandatory result prevents
overall `PASS`. The runner maps each failure to case/check or system-check ID, requirement/invariant,
expected behavior, actual behavior, and suggested repair area.

## Harness-Driven Repair Loop

For each failed evaluation case, the harness/repair handoff must contain:

- Evaluation case ID
- Input message
- Generated output
- Failed requirement or invariant
- Expected behavior
- Actual behavior
- Suggested repair area
- Relevant model/configuration metadata without credentials

The coding agent must use this evidence to propose the narrowest repair, add or adjust focused tests,
rerun the smallest applicable test set, rerun the full harness, and preserve the failed/difficult
case in the dataset. It must not delete cases, weaken prompts/rubrics, lower thresholds, or
bypass a guardrail to achieve PASS.

## Harness Evidence and Human Acceptance

`evidence/harness-log.md` must record:

- Application triage provider and configuration name, without secrets
- Semantic evaluator model identifier/version and rubric version, without secrets
- Execution date and runner version
- Declared thresholds
- Schema, behavioral, classification, semantic, and separate system-verification statuses/results
- Meaningful failures and repair actions
- Re-evaluation results
- Known limitations and risks
- Final human `ACCEPT` or `REJECT` decision

`evidence/initial-generation/` and `evidence/final-generation/` hold reproducible generated outputs
and logs. `evidence/eval-results.json` is the machine-readable final report.

No feature or evaluation is considered passed merely because the plan exists. Final evidence will
be generated only during implementation/evaluation and must report actual results.

## Requirement and Acceptance Traceability

| Component | Requirements | Acceptance/Success coverage |
|---|---|---|
| Input validation | FR-001, FR-007 | Empty input returns 422/no result/no retention |
| Dominant triage | FR-002, FR-003, FR-004, FR-005 | Category/routing/priority/sentiment accepted values |
| Evidence and clarification | FR-006, FR-008 | Grounded rationale and focused clarification |
| Security guardrails | FR-009, FR-010 | Human review; no secret repetition; no prohibited actions |
| Response contract | FR-007, FR-011 | Nine-field JSON, concise/professional output |
| Evaluation | FR-012 through FR-014, FR-016 | Dataset, independent layers, fixed rubric, traceability |
| Retention/auth | FR-015 | Authenticated support-reviewer access, role denial, expired-record deletion, and 30-day retention |
| Success measurement | SC-001 through SC-008 | Threshold and reporting checks |

## Testing Strategy

- Contract tests validate schema shape and category/department/clarification conditionals.
- Unit tests cover provider parsing, enum mapping, priority rules, clarification, and empty input.
- Behavioral tests cover multiple issues, security-sensitive messages, prohibited actions,
  malformed provider output, and unavailable providers.
- Integration tests cover FastAPI routes, SQLite persistence, authentication, authorization, and
  deletion.
- System-level runner checks explicitly verify authenticated reviewer access, unauthenticated
  denial, unauthorized-role denial, and expired-record deletion; report these separately from
  model-generated triage case scores.
- Security tests cover unauthenticated/non-reviewer access and secret non-disclosure.
- Evaluation tests verify that dataset IDs, traceability IDs, layer independence, and threshold
  reporting are present, including semantic `BLOCKED`/`INCOMPLETE` handling and the overall gate.

## Security and Privacy

- Environment variables supply model credentials and signing/session secrets.
- Bearer tokens/sessions expire and are not included in logs.
- Retained message text is limited to the approved 30-day audit window.
- Credential-like strings must not be copied into suggested responses or evidence.
- Provider exceptions must not expose credentials or internal stack traces.
- The application exposes no transaction or account-administration operation.

## Implementation Phases

### Phase 0: Research and decisions

- Confirm Python/FastAPI/SQLite/provider dependencies and the JSON Schema draft.
- Document mock and real provider tradeoffs.
- Define pre-evaluation thresholds and case traceability format.

### Phase 1: Design artifacts

- Complete data model and API/JSON contract.
- Add evaluation case design and repair-evidence format.
- Re-check constitution and specification traceability.

### Phase 2: Implementation readiness

- Create source modules, tests, provider adapters, database migration/setup, and prompt files.
- Add `requirements.txt`, safe `.env.example` placeholders, `.gitignore` entries for environments,
  caches, local databases, and `.env`, and a `README.md` covering setup, configuration, startup,
  tests, and evaluation.
- Create at least 15 evaluation cases in `evals/dataset.json`.
- Implement and document the one-run harness.

### Phase 3: Initial evaluation

- Run application triage in mock mode first for deterministic evaluation inputs.
- Keep semantic scoring separate: use its fixed configured model and rubric even when the
  application triage provider is mocked. If it is unavailable or invalid, record `BLOCKED` or
  `INCOMPLETE`; that run cannot claim overall `PASS` without semantic completion.
- Capture initial evidence and realistic limitations.
- Repair only from harness evidence while preserving guardrails.

### Phase 4: Final evaluation and human acceptance

- Re-run all layers with the selected provider/mock mode.
- Write final machine-readable evidence and harness log.
- Record human ACCEPT/REJECT and unresolved risks. Do not claim pass until evidence is complete.

## Dependencies

- Python 3.12 virtual environment
- FastAPI, Pydantic, `jsonschema`, `pytest`
- Optional real AI provider SDK/API compatible with the selected adapter
- SQLite standard library support
- Assignment environment support for environment variables

## Risks

- **Model output drift**: Bounded parsing and independent schema/behavioral validation mitigate it.
- **Semantic evaluator variance**: Use a fixed rubric, request brief reasons, and never use semantic
  scores to waive deterministic failures.
- **Credential availability**: Mock application provider enables offline development and
  deterministic tests; full evaluation remains `BLOCKED`/`INCOMPLETE` if the required semantic
  evaluator is unavailable.
- **Sensitive input**: Redact logs/evidence and prevent output repetition.
- **Retention enforcement**: An external hourly scheduler is required. Failures/overdue records are
  monitored and retried; physical deletion cannot be guaranteed while the scheduler, host, or
  database is unavailable.
- **Difficult-case loss**: Repaired cases remain in the dataset and must be re-evaluated.

## Unresolved Questions

- No implementation-blocking unresolved question is identified.
- The eventual provider/model name and credentials remain intentionally unspecified because no real
  API key is assumed.
- Initial reviewer provisioning and local token/session secret naming will be implementation
  configuration choices within the lightweight scope.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| None | The plan follows the constitution and keeps optional infrastructure out of scope. | No identity provider, distributed queue, or external database is needed. |

## Project Structure

### Spec Kit artifacts

```text
specs/001-ai-support-ticket-triage/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/
    ├── openapi.yaml
    └── triage-result.schema.json
```

### Project artifacts

```text
Assignment/Part-1B/
├── .specify/
├── src/
├── prompts/
├── tests/
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── evals/dataset.json
├── .harness/
├── evidence/
│   ├── initial-generation/
│   ├── final-generation/
│   ├── eval-results.json
│   └── harness-log.md
└── specs/001-ai-support-ticket-triage/
```
