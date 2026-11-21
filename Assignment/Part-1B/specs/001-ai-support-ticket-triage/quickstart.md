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
- Configure the host scheduler (for example, Windows Task Scheduler or cron) to run
  `python -m src.persistence.retention --cleanup-expired` at least hourly. The cleanup process
  deletes records at or past `delete_after`, emits a monitoring event, and exits nonzero on failure.
  It runs independently of the API process, so it can continue during an application outage when
  the scheduler and SQLite database remain available.
- Monitor cleanup failures and overdue-record count/oldest deadline. A failed attempt is retried by
  the next hourly run. Startup cleanup is an additional safeguard; retained-record reads also
  prevent expired records from being returned.
- The scheduler, host, and SQLite availability are operational dependencies. If the scheduler or
  host is unavailable, or SQLite cannot be accessed, physical deletion by the deadline cannot be
  guaranteed. Detect overdue records and run cleanup after service/database recovery; do not
  describe this as an unconditional guarantee.

## Evaluation

Run the one evaluation runner. It independently reports schema/Pydantic conformance,
behavioral-invariant results, per-field classification agreement, fixed-rubric semantic scores,
system-level verification, and case-level repair evidence. Each mandatory layer and the overall
result use these states:

- `PASS`: completed and met the declared threshold.
- `FAIL`: completed but failed an assertion or threshold.
- `BLOCKED`: a required service, configuration, or credential was unavailable.
- `INCOMPLETE`: execution did not produce all valid required results.

Overall `PASS` requires every mandatory evaluation layer and system-level check to complete and
meet its declared threshold. Any mandatory `FAIL`, `BLOCKED`, or `INCOMPLETE` prevents overall
`PASS`; a missing semantic evaluator must not be skipped or replaced with fabricated scores.
