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
- `category`: evaluation category
- `message`: input string
- `expected`: labels and behavioral assertions
- `traceability`: FR/SC IDs and behavioral-invariant IDs
- `semantic_expectations`: fixed-rubric expectations

## EvaluationFailure

- `case_id`
- `input_message`
- `generated_output`
- `failed_requirement_or_invariant`
- `failed_check`
- `expected_behavior`
- `actual_behavior`
- `suggested_repair_area`

## EvaluationReport

- Schema section
- Behavioral section
- Classification agreement section
- Semantic section
- Aggregate PASS/FAIL
- Failure details
- Configuration metadata without secrets
