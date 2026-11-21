# Phase 1 Data Model

## CustomerMessage

- `id`: UUID
- `text`: non-empty, non-whitespace string
- `created_at`: UTC timestamp

Whitespace-only input is rejected and never persisted.

## TriageResult

- `category`: PAYMENT, DELIVERY, ACCOUNT, TECHNICAL, GENERAL
- `priority`: LOW, MEDIUM, HIGH, CRITICAL
- `sentiment`: POSITIVE, NEUTRAL, NEGATIVE
- `department`: category-mapped support department
- `suggested_response`: non-empty string
- `rationale`: non-empty string
- `clarification_required`: boolean
- `clarification_question`: non-empty string or null
- `human_review_required`: boolean

Exactly nine fields are allowed in the external contract.

## RetainedRecord

- `id`: UUID
- `customer_message_id`: UUID
- `triage_result_id`: UUID
- `created_at`: UTC timestamp
- `delete_after`: `created_at + 30 days`

Access requires authentication and the `support-reviewer` role.

## ReviewerPrincipal

- `principal_id`: UUID or stable local identifier
- `username`: local identifier
- `role`: must contain `support-reviewer` for retained-record access
- `credential/session_reference`: secret-bearing data; never printed or placed in evidence

## EvaluationCase

- `case_id`: stable string
- `category`: normal, boundary, ambiguous, underspecified, missing-information,
  malformed-provider-output, security-sensitive, or adversarial
- `message`: valid customer-message string for a triage-result case
- `expected`: labels and behavioral assertions
- `traceability`: FR/SC IDs and behavioral-invariant IDs
- `semantic_expectations`: fixed-rubric expectations
- `expected_outcome`: `triage_result` or `provider_rejected`
- `provider_output_fixture`: optional fixture containing `adapter: deterministic_fake` and
  `raw_response: string`. It is required for `malformed-provider-output` cases, whose
  `expected_outcome` must be `provider_rejected`. The harness injects this exact raw response
  through the fake provider, bypassing any real model call. The customer message remains valid;
  malformed provider output is not malformed customer input. Empty/whitespace-only customer
  messages are request-validation tests, not triage-result evaluation cases.

## EvaluationCaseResult

- `case_id`
- `outcome`: `PASS`, `FAIL`, `BLOCKED`, or `INCOMPLETE`
- `structural_observation`: valid, invalid with failure code, or not applicable
- `actual_behavior`: observed service response/error and whether a triage result was persisted
- `failure_details`: requirement/invariant/check, expected behavior, actual behavior, and suggested
  repair area when applicable

For a malformed-provider-output fixture, the structural evaluator records the raw response's
parse/schema failure and checks that the application returns a safe provider error without
persisting a triage result. The case outcome is `PASS` only if the invalid response is rejected;
accepting it as a triage result or returning a success-shaped fallback gives the case `FAIL` and
fails the structural layer.

## EvaluationFailure

- `case_id`
- `input_message`
- `generated_output`
- `failed_requirement_or_invariant`
- `failed_check`
- `expected_behavior`
- `actual_behavior`
- `suggested_repair_area`
- `provider_output_fixture`: included when relevant, without credentials or customer secrets

## EvaluationReport

- Case results, including the case outcome and any expected structural-failure observation
- Schema section
- Behavioral section
- Classification agreement section
- Semantic section
- Separate system-level verification section
- Each mandatory section and the overall report use `PASS`, `FAIL`, `BLOCKED`, or `INCOMPLETE`
- Overall `PASS` is allowed only if every mandatory section and system-level check completes and
  meets its declared threshold. Any mandatory `FAIL`, `BLOCKED`, or `INCOMPLETE` prevents overall
  `PASS`.
- Failure details
- Configuration metadata without secrets

Status meanings:

- `PASS`: completed successfully and met the declared threshold.
- `FAIL`: completed, but at least one assertion or threshold failed.
- `BLOCKED`: required service, configuration, or credential was unavailable.
- `INCOMPLETE`: execution did not produce all valid required results.

## CleanupRun

- `started_at`, `finished_at`: UTC timestamps
- `status`: success or failure
- `deleted_count`, `overdue_count`: record counts
- `oldest_overdue_delete_after`: UTC timestamp or null
- `error_code`: non-sensitive operational failure identifier or null

Emit one structured monitoring event per cleanup attempt without customer message text or
credentials. Use process/host logs so a database-access failure can itself still be reported.
Failed attempts exit unsuccessfully and are retried by the next scheduled invocation.
