# Phase 1 Quickstart

## Triage

Send a non-empty support message to `POST /triage`.

- Valid input receives one JSON triage result.
- Empty/whitespace-only input receives 422 and creates no retained record.
- Provider unavailable/malformed output receives a safe error and does not invent a result.

## Retained records

Authenticate with a local session or bearer token mapped to `support-reviewer`.

- Unauthenticated reads return 401.
- Authenticated non-reviewers return 403.
- Records expire no later than 30 days after creation.

## Evaluation

Run the one evaluation runner. It independently reports schema/Pydantic conformance,
behavioral-invariant results, per-field classification agreement, fixed-rubric semantic scores,
aggregate PASS/FAIL, and case-level repair evidence.
