# AI Customer Support Ticket Triage

A small Python 3.12 FastAPI service that classifies customer support messages, validates a strict
JSON result, and provides authenticated support-reviewer access to records retained for a maximum
of 30 days.

## Setup

From `Assignment/Part-1B`:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` before use. The example contains placeholders only. Keep real credentials out of source,
fixtures, screenshots, logs, and evaluation evidence. The application defaults to the deterministic
`mock` provider. No real model key is required for local development or unit tests.

To enable application-provider calls, configure `TRIAGE_PROVIDER=openai_compatible` plus
`AI_BASE_URL`, `AI_MODEL`, and `AI_API_KEY` for an OpenAI-compatible chat-completions endpoint.
Requests use a bounded timeout and retry count. Provider failures or malformed responses produce a
safe error; they never create a fabricated triage result.

Semantic evaluation is a separate required model call. Configure
`SEMANTIC_EVALUATOR_BASE_URL`, `SEMANTIC_EVALUATOR_MODEL`, and
`SEMANTIC_EVALUATOR_API_KEY`; keep the model identifier fixed for comparable runs. The rubric
version is fixed at `1`; other values are rejected. The application mock is never used to generate
semantic scores.

For retained-record access, configure `REVIEWER_CREDENTIALS_JSON` as a JSON array of local
`username`/`token`/`role` entries. Use a high-entropy token and the `support-reviewer` role for
reviewer access. Tokens are stored in SQLite only as SHA-256 digests. A configured identity with a
different role is authenticated but receives 403 on retained-record access.

## Start the API

```powershell
uvicorn src.api.app:create_app --factory --reload
```

`POST /triage` accepts `{"message": "..."}`. Empty and whitespace-only messages return 422 without
provider invocation or persistence. Successful responses include the generated record identifier
in the `X-Record-ID` response header without changing the nine-field JSON body.
`GET /retained/{record_id}` requires a bearer token for a configured `support-reviewer` credential.
In `/docs`, use **Authorize** and paste the configured token (without the `Bearer ` prefix), then submit the exact record ID
from the triage response's `X-Record-ID` header; record IDs are UUIDs, not numeric sequence values.
Do not remove the authentication requirement to work around a 401. No transaction processing or
account administration endpoint is provided.

## Web console

Open `http://127.0.0.1:8000/` in a browser after starting the API. The console provides a
ticket-triage workspace and an authenticated retained-record lookup. The same `/triage` and
`/retained/{record_id}` endpoints power both the console and API clients.

## Retention cleanup

The independent cleanup command is:

```powershell
python -m src.persistence.retention --cleanup-expired
```

Configure Windows Task Scheduler to run this command at least hourly with the Part-1B directory as
the working directory and the same environment/database configuration as the API. On a
Unix-like host, an equivalent hourly cron entry may be used. The command deletes records when
`delete_after` is reached, logs cleanup outcomes without customer messages or credentials, exits
nonzero on failure, and retries on the next scheduled invocation. Startup cleanup and expiration
checks before record access are additional safeguards.

Monitor cleanup failure logs and overdue-record count/oldest deadline. The scheduler, host, and
SQLite availability are operational dependencies. If the scheduler or host is unavailable, or the
database cannot be accessed, deletion by the deadline cannot be guaranteed. Detect overdue records
and run cleanup after recovery; never return expired records. The cleanup process can run while the
API process is unavailable if the scheduler and database remain available.

## Tests

```powershell
python -m pytest
```

Tests use temporary SQLite databases and deterministic provider fixtures; they do not call an
external AI provider. Coverage includes empty input, malformed provider output, multiple issues,
clarification, security-sensitive messages, prohibited actions, reviewer authorization, retention,
evaluation statuses, and the evaluation dataset.

## Evaluation

Run the one evaluation harness:

```powershell
python .harness\run-evaluation.py --phase initial
python .harness\run-evaluation.py --phase final
```

Record each actual repair on the re-evaluation command with one `--repair-action` option per
repair. Use non-sensitive descriptions; they are written to the report and harness log.

The runner executes structural/schema, behavioral-invariant, classification-agreement,
fixed-rubric semantic, and separate system-level authentication/retention checks. Thresholds are
fixed in `src/evaluation/report.py` and `.harness/config.example.json`. Overall `PASS` requires
every mandatory layer and system check to complete and meet its threshold. Each layer reports
`PASS`, `FAIL`, `BLOCKED`, or `INCOMPLETE`; missing semantic credentials produce `BLOCKED`, and an
invalid semantic response produces `INCOMPLETE`. Neither state can become overall `PASS`.

The machine-readable report is `evidence/eval-results.json`; run outputs are recorded under
`evidence/initial-generation/` and `evidence/final-generation/`, and run metadata/statuses append to
`evidence/harness-log.md`. Case-level failures include traceability, expected/actual behavior, and
a suggested repair area. Preserve difficult cases and thresholds during repairs. No evaluation
results are created until the harness is run.

After reviewing actual evidence and limitations, a human may record a decision explicitly:

```powershell
python .harness\run-evaluation.py --phase final --human-decision REJECT
```

Use `ACCEPT` or `REJECT` only after human review; the runner defaults to `PENDING` and never invents
an acceptance decision. A human decision does not change mandatory evaluation layer statuses.

## Evaluation traceability IDs

The dataset uses these behavioral invariant identifiers:

| ID | Invariant |
|---|---|
| BI-001 | Allowed classification values and category-to-department mapping |
| BI-002 | Clarification is focused and only required when material |
| BI-003 | Security-sensitive cases require human review and do not repeat secrets |
| BI-004 | Prohibited transactions/account modifications are not claimed as completed |
| BI-005 | Multiple issues receive one dominant classification |
| BI-006 | Invalid provider output is rejected without persisting a result |
| BI-007 | Empty input is rejected before provider invocation or persistence |
| BI-008 | Retained-record access requires the support-reviewer role and expiration |

Each dataset case also names applicable functional-requirement and invariant IDs.
