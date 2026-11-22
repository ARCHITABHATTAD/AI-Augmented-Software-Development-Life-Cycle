from __future__ import annotations

from typing import Any

from src.domain.triage import TriageResult
from src.evaluation.models import EvaluationCase
from src.evaluation.report import FAIL, PASS, THRESHOLDS, new_failure

CLASSIFICATION_FIELDS = ("category", "priority", "sentiment", "department")


def evaluate_classification(
    cases: list[EvaluationCase], outputs: dict[str, TriageResult | None]
) -> dict[str, Any]:
    field_matches = {field: 0 for field in CLASSIFICATION_FIELDS}
    field_counts = {field: 0 for field in CLASSIFICATION_FIELDS}
    failures: list[dict[str, Any]] = []
    for case in cases:
        if case.expected_outcome != "triage_result":
            continue
        result = outputs.get(case.case_id)
        if result is None:
            failures.append(
                new_failure(
                    case_id=case.case_id,
                    message=case.message,
                    output=None,
                    check="CLASSIFICATION_RESULT_MISSING",
                    expected="classification result for the case",
                    actual="no result",
                    suggested_repair_area="provider and triage orchestration",
                    requirements=case.traceability.requirements,
                    invariants=case.traceability.invariants,
                )
            )
            for field in CLASSIFICATION_FIELDS:
                field_counts[field] += 1
            continue
        actual_values = result.model_dump(mode="json")
        for field in CLASSIFICATION_FIELDS:
            expected_value = case.expected.labels.get(field)
            if expected_value is None:
                continue
            field_counts[field] += 1
            if actual_values[field] == expected_value:
                field_matches[field] += 1
            else:
                failures.append(
                    new_failure(
                        case_id=case.case_id,
                        message=case.message,
                        output=actual_values,
                        check=f"CLASSIFICATION_{field.upper()}_AGREEMENT",
                        expected=expected_value,
                        actual=actual_values[field],
                        suggested_repair_area="triage classification or reviewed case label",
                        requirements=case.traceability.requirements,
                        invariants=case.traceability.invariants,
                    )
                )
    rates = {
        field: (
            field_matches[field] / field_counts[field] if field_counts[field] else 0.0
        )
        for field in CLASSIFICATION_FIELDS
    }
    thresholds_met = all(
        rates[field] >= THRESHOLDS["classification_agreement_per_field"]
        for field in CLASSIFICATION_FIELDS
    )
    return {
        "status": FAIL if failures or not thresholds_met else PASS,
        "metrics": {
            "agreement_rates": rates,
            "matches": field_matches,
            "cases_compared": field_counts,
            "threshold": THRESHOLDS["classification_agreement_per_field"],
        },
        "case_results": [],
        "failure_details": failures,
    }
