
# Part 1A - Deterministic Harness

## Purpose
Independently validate the Home Inventory & Stock Management
System against its engineering and functional requirements.

## Validation Gates

1. Ruff: Syntax and lint validation.
2. Bandit: Static application security analysis.
3. Pytest: Unit and API contract testing.

## Execution

Activate the project's virtual environment and run:

powershell -ExecutionPolicy Bypass -File .harness/run-harness.ps1

## Results

Timestamped execution logs are stored in:

evidence/harness-results/

## Acceptance Rule

All mandatory harness gates must pass before the
implementation is recommended for human acceptance.

The final ACCEPT/REJECT decision is made by a human reviewer.
