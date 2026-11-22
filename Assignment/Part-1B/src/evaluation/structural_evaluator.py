from __future__ import annotations

import json
from typing import Any

from src.domain.triage import TriageResult
from src.domain.validation import ProviderOutputError, validate_provider_output
from src.evaluation.models import EvaluationCase
from src.evaluation.report import BLOCKED, FAIL, INCOMPLETE, PASS, new_failure


def evaluate_structural_case(
    case: EvaluationCase,
    raw_output: str | None,
    result: TriageResult | None,
    error_type: str | None,
    persisted: bool,
) -> dict[str, Any]:
    trace = case.traceability
    if case.expected_outcome == "provider_rejected":
        structural_observation: dict[str, Any] = {
            "valid": False,
            "failure_code": "SCHEMA_INVALID_PROVIDER_RESPONSE",
        }
        parse_failure = False
        if raw_output is None:
            parse_failure = True
            structural_observation["failure_code"] = "SCHEMA_PROVIDER_RESPONSE_MISSING"
        else:
            try:
                validate_provider_output(raw_output)
            except ProviderOutputError as exc:
                structural_observation["failure_code"] = _failure_code(exc, raw_output)
            else:
                parse_failure = True
                structural_observation = {
                    "valid": True,
                    "failure_code": None,
                }

        rejected_safely = (
            not parse_failure
            and error_type == "ProviderOutputError"
            and result is None
            and not persisted
        )
        failure = [] if rejected_safely else [
            new_failure(
                case_id=case.case_id,
                message=case.message,
                output=raw_output,
                check="SCHEMA_MALFORMED_PROVIDER_OUTPUT_REJECTION",
                expected="invalid provider output rejected; no result persisted",
                actual={
                    "error_type": error_type,
                    "result_returned": result is not None,
                    "persisted": persisted,
                    "structural_observation": structural_observation,
                },
                suggested_repair_area="provider output parser and API error handling",
                requirements=trace.requirements,
                invariants=trace.invariants,
            )
        ]
        return {
            "case_id": case.case_id,
            "expected_outcome": case.expected_outcome,
            "outcome": PASS if rejected_safely else FAIL,
            "structural_observation": structural_observation,
            "failure_details": failure,
        }

    if error_type == "ProviderUnavailable":
        return {
            "case_id": case.case_id,
            "expected_outcome": case.expected_outcome,
            "outcome": BLOCKED,
            "structural_observation": {"valid": None, "failure_code": "SCHEMA_PROVIDER_BLOCKED"},
            "failure_details": [],
        }
    if result is None or raw_output is None:
        failure = new_failure(
            case_id=case.case_id,
            message=case.message,
            output=raw_output,
            check="SCHEMA_RESULT_MISSING",
            expected="one valid triage result",
            actual={"error_type": error_type, "result_returned": result is not None},
            suggested_repair_area="provider parsing and triage orchestration",
            requirements=trace.requirements,
            invariants=trace.invariants,
        )
        return {
            "case_id": case.case_id,
            "expected_outcome": case.expected_outcome,
            "outcome": INCOMPLETE if error_type is None else FAIL,
            "structural_observation": {"valid": False, "failure_code": "SCHEMA_RESULT_MISSING"},
            "failure_details": [failure],
        }

    try:
        validate_provider_output(raw_output)
        TriageResult.model_validate(result.model_dump(mode="json"))
        schema_valid = True
        code = None
    except (ProviderOutputError, ValueError, TypeError) as exc:
        schema_valid = False
        code = _failure_code(exc, raw_output)
    failure_details = [] if schema_valid else [
        new_failure(
            case_id=case.case_id,
            message=case.message,
            output=raw_output,
            check=code or "SCHEMA_INVALID_RESULT",
            expected="raw provider output and returned result conform to the schema",
            actual=str(code or "validation failed"),
            suggested_repair_area="provider output parsing and result contract",
            requirements=trace.requirements,
            invariants=trace.invariants,
        )
    ]
    return {
        "case_id": case.case_id,
        "expected_outcome": case.expected_outcome,
        "outcome": PASS if schema_valid else FAIL,
        "structural_observation": {"valid": schema_valid, "failure_code": code},
        "failure_details": failure_details,
    }


def aggregate_structural(results: list[dict[str, Any]]) -> dict[str, Any]:
    outcomes = [result["outcome"] for result in results]
    if FAIL in outcomes:
        status = FAIL
    elif BLOCKED in outcomes:
        status = BLOCKED
    elif INCOMPLETE in outcomes:
        status = INCOMPLETE
    else:
        status = PASS
    eligible = [
        result
        for result in results
        if result["expected_outcome"] == "triage_result"
        and result["structural_observation"]["valid"] is not None
    ]
    schema_valid = sum(
        1 for result in eligible if result["structural_observation"]["valid"] is True
    )
    denominator = len(eligible)
    rate = 1.0 if denominator == 0 else schema_valid / denominator
    return {
        "status": status,
        "metrics": {
            "schema_conformance_rate": rate,
            "cases_evaluated": len(results),
        },
        "case_results": results,
        "failure_details": [
            failure
            for result in results
            for failure in result.get("failure_details", [])
        ],
    }


def _failure_code(exc: Exception, raw_output: str | None) -> str:
    message = str(exc).lower()
    if raw_output is not None:
        try:
            parsed = json.loads(raw_output)
        except json.JSONDecodeError:
            return "SCHEMA_INVALID_JSON"
        if not isinstance(parsed, dict):
            return "SCHEMA_NOT_OBJECT"
    if "required" in message or "field required" in message:
        return "SCHEMA_MISSING_FIELD"
    if "additional properties" in message or "extra inputs" in message:
        return "SCHEMA_EXTRA_FIELD"
    if "enum" in message or "input should be" in message:
        return "SCHEMA_INVALID_VALUE"
    return "SCHEMA_CONTRACT_VIOLATION"
