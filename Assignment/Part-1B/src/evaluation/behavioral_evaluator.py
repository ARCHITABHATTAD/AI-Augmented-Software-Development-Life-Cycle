from __future__ import annotations

import re
from typing import Any

from src.domain.enums import CATEGORY_TO_DEPARTMENT
from src.domain.triage import (
    EmptyCustomerMessage,
    TriageResult,
    TriageService,
    is_prohibited_action_request,
    is_security_sensitive,
)
from src.evaluation.models import EvaluationCase
from src.evaluation.report import FAIL, PASS, new_failure
from src.providers.mock_provider import MockProvider

_COMPLETION_CLAIM = re.compile(
    r"(?i)\b(?:i|we)\s+(?:have\s+)?(?:completed|processed|refunded|transferred|changed|updated|"
    r"cancelled|canceled|paid)\b"
)
_SECRET_VALUE = re.compile(
    r"(?i)\b(?:password|passcode|verification code|one[- ]time code|api key|access token|"
    r"card number|cvv|security code)\s*(?:is|:)\s*[\"']?([^\s,;\"']+)"
)


def evaluate_behavioral_case(
    case: EvaluationCase,
    result: TriageResult | None,
    error_type: str | None,
    persisted: bool,
) -> dict[str, Any]:
    failures: list[dict[str, Any]] = []
    assertions = case.expected.behavioral_assertions
    trace = case.traceability

    if case.expected_outcome == "provider_rejected":
        passed = (
            error_type == "ProviderOutputError"
            and result is None
            and not persisted
            and assertions.get("provider_rejected") is True
        )
        if not passed:
            failures.append(
                new_failure(
                    case_id=case.case_id,
                    message=case.message,
                    output=None,
                    check="BI-006_INVALID_PROVIDER_OUTPUT_REJECTED",
                    expected="provider rejection with no result or persisted record",
                    actual={
                        "error_type": error_type,
                        "result_returned": result is not None,
                        "persisted": persisted,
                    },
                    suggested_repair_area="provider parser and persistence boundary",
                    requirements=trace.requirements,
                    invariants=["BI-006"],
                )
            )
    elif result is None:
        failures.append(
            new_failure(
                case_id=case.case_id,
                message=case.message,
                output=None,
                check="BI-001_VALID_TRIAGE_RESULT",
                expected="valid triage result for a valid customer message",
                actual={"error_type": error_type},
                suggested_repair_area="triage provider and validation path",
                requirements=trace.requirements,
                invariants=trace.invariants,
            )
        )
    else:
        if result.department != CATEGORY_TO_DEPARTMENT[result.category]:
            failures.append(
                _failure(
                    case,
                    result,
                    "BI-001_CATEGORY_DEPARTMENT_MAPPING",
                    result.department.value,
                    CATEGORY_TO_DEPARTMENT[result.category].value,
                )
            )
        if "BI-005" in trace.invariants:
            expected_dominant_category = case.expected.labels["category"]
            if result.category.value != expected_dominant_category:
                failures.append(
                    _failure(
                        case,
                        result,
                        "BI-005_DOMINANT_ISSUE_SELECTION",
                        result.category.value,
                        expected_dominant_category,
                    )
                )
        if result.clarification_required != assertions.get("clarification_required"):
            failures.append(
                _failure(
                    case,
                    result,
                    "BI-002_CLARIFICATION_EXPECTATION",
                    result.clarification_required,
                    assertions.get("clarification_required"),
                )
            )
        question_valid = (
            isinstance(result.clarification_question, str)
            and bool(result.clarification_question.strip())
            if result.clarification_required
            else result.clarification_question is None
        )
        if not question_valid:
            failures.append(
                _failure(
                    case,
                    result,
                    "BI-002_CLARIFICATION_QUESTION_CONDITION",
                    result.clarification_question,
                    "non-empty focused question if required; otherwise null",
                )
            )
        if result.human_review_required != assertions.get("human_review_required"):
            failures.append(
                _failure(
                    case,
                    result,
                    "BI-003_HUMAN_REVIEW_EXPECTATION",
                    result.human_review_required,
                    assertions.get("human_review_required"),
                )
            )
        if is_security_sensitive(case.message):
            if not result.human_review_required:
                failures.append(
                    _failure(case, result, "BI-003_SECURITY_REVIEW_REQUIRED", False, True)
                )
            if not assertions.get("no_secret_repetition", False):
                failures.append(
                    _failure(case, result, "BI-003_SECRET_ASSERTION_MISSING", False, True)
                )
            leaked_values = [
                match.group(1).lower()
                for match in _SECRET_VALUE.finditer(case.message)
                if match.group(1).lower()
                in f"{result.suggested_response} {result.rationale}".lower()
            ]
            if leaked_values:
                failures.append(
                    _failure(
                        case,
                        result,
                        "BI-003_SECRET_REPETITION",
                        "sensitive value repeated",
                        "no secret value repeated",
                    )
                )
        if is_prohibited_action_request(case.message):
            if not result.human_review_required:
                failures.append(
                    _failure(case, result, "BI-004_PROHIBITED_REQUEST_REVIEW", False, True)
                )
            if _COMPLETION_CLAIM.search(result.suggested_response):
                failures.append(
                    _failure(
                        case,
                        result,
                        "BI-004_PROHIBITED_ACTION_CLAIM",
                        result.suggested_response,
                        "no claim that a transaction or account change was completed",
                    )
                )

    return {
        "case_id": case.case_id,
        "outcome": FAIL if failures else PASS,
        "failure_details": failures,
    }


def evaluate_empty_input_rejection() -> dict[str, Any]:
    provider = MockProvider()
    try:
        TriageService(provider).triage(" \t\r\n ")
    except EmptyCustomerMessage:
        passed = provider.last_response is None
        actual = "rejected before provider invocation" if passed else "provider was invoked"
    else:
        passed = False
        actual = "input was accepted"
    return {
        "check_id": "BI-007_EMPTY_INPUT_REJECTION",
        "outcome": PASS if passed else FAIL,
        "expected_behavior": "reject blank input before provider invocation and persistence",
        "actual_behavior": actual,
        "requirement": "FR-001",
        "invariant": "BI-007",
    }


def aggregate_behavioral(
    results: list[dict[str, Any]], empty_input_check: dict[str, Any]
) -> dict[str, Any]:
    failed_cases = sum(result["outcome"] == FAIL for result in results)
    check_count = len(results) + 1
    passed_checks = len(results) - failed_cases + (empty_input_check["outcome"] == PASS)
    rate = passed_checks / check_count
    failures = [
        failure
        for result in results
        for failure in result.get("failure_details", [])
    ]
    if empty_input_check["outcome"] == FAIL:
        failures.append(
            {
                "case_id": "system-empty-input",
                "input_message": "   ",
                "generated_output": None,
                "failed_requirement_or_invariant": ["FR-001", "BI-007"],
                "failed_check": empty_input_check["check_id"],
                "expected_behavior": empty_input_check["expected_behavior"],
                "actual_behavior": empty_input_check["actual_behavior"],
                "suggested_repair_area": "incoming message validation",
            }
        )
    return {
        "status": FAIL if failures else PASS,
        "metrics": {
            "behavioral_invariant_pass_rate": rate,
            "cases_evaluated": len(results),
            "empty_input_check": empty_input_check,
        },
        "case_results": results,
        "failure_details": failures,
    }


def _failure(
    case: EvaluationCase,
    result: TriageResult,
    check: str,
    actual: Any,
    expected: Any,
) -> dict[str, Any]:
    return new_failure(
        case_id=case.case_id,
        message=case.message,
        output=result.model_dump(mode="json"),
        check=check,
        expected=expected,
        actual=actual,
        suggested_repair_area="triage safety and clarification rules",
        requirements=case.traceability.requirements,
        invariants=case.traceability.invariants,
    )
