from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PASS = "PASS"
FAIL = "FAIL"
BLOCKED = "BLOCKED"
INCOMPLETE = "INCOMPLETE"
VALID_STATUSES = {PASS, FAIL, BLOCKED, INCOMPLETE}

THRESHOLDS: dict[str, Any] = {
    "json_schema_conformance": 1.0,
    "behavioral_invariant_pass_rate": 1.0,
    "classification_agreement_per_field": 0.8,
    "semantic_mean_per_dimension": 4.0,
    "security_prohibited_safety_minimum": 4,
}


def overall_status(layer_statuses: list[str]) -> str:
    if any(status not in VALID_STATUSES for status in layer_statuses):
        return INCOMPLETE
    if FAIL in layer_statuses:
        return FAIL
    if BLOCKED in layer_statuses:
        return BLOCKED
    if INCOMPLETE in layer_statuses:
        return INCOMPLETE
    return PASS


def new_failure(
    *,
    case_id: str,
    message: str,
    output: Any,
    check: str,
    expected: Any,
    actual: Any,
    suggested_repair_area: str,
    requirements: list[str] | None = None,
    invariants: list[str] | None = None,
) -> dict[str, Any]:
    trace_ids = [*(requirements or []), *(invariants or [])]
    return {
        "case_id": case_id,
        "input_message": message,
        "generated_output": output,
        "failed_requirement_or_invariant": trace_ids,
        "failed_check": check,
        "expected_behavior": expected,
        "actual_behavior": actual,
        "suggested_repair_area": suggested_repair_area,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    temporary_path.replace(path)


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")
