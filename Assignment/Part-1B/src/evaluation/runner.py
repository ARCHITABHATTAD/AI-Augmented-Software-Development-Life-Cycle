from __future__ import annotations

import argparse
import json
import logging
import tempfile
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from src.api.app import create_app
from src.config import ReviewerCredential, Settings
from src.domain.triage import TriageResult, TriageService
from src.evaluation.behavioral_evaluator import (
    aggregate_behavioral,
    evaluate_behavioral_case,
    evaluate_empty_input_rejection,
)
from src.evaluation.classification_evaluator import evaluate_classification
from src.evaluation.invariants import INVARIANT_REQUIREMENTS, INVARIANTS
from src.evaluation.models import EvaluationCase, EvaluationDataset
from src.evaluation.report import (
    FAIL,
    INCOMPLETE,
    PASS,
    THRESHOLDS,
    overall_status,
    utc_now_iso,
    write_json,
)
from src.evaluation.semantic_evaluator import evaluate_semantics
from src.evaluation.structural_evaluator import (
    aggregate_structural,
    evaluate_structural_case,
)
from src.persistence.database import SQLiteRepository
from src.providers.mock_provider import MockProvider

LOGGER = logging.getLogger(__name__)
RUNNER_VERSION = "1.0.0"
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = ROOT / "evals" / "dataset.json"
EXPECTED_CATEGORIES = {
    "PAYMENT",
    "DELIVERY",
    "ACCOUNT",
    "TECHNICAL",
    "GENERAL",
}
EXPECTED_PRIORITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
EXPECTED_SENTIMENTS = {"POSITIVE", "NEUTRAL", "NEGATIVE"}
ALLOWED_REQUIREMENTS = {f"FR-{number:03d}" for number in range(1, 17)} | {
    f"SC-{number:03d}" for number in range(1, 9)
}


def load_dataset(path: Path = DEFAULT_DATASET) -> EvaluationDataset:
    dataset = EvaluationDataset.model_validate_json(path.read_text(encoding="utf-8"))
    case_ids = [case.case_id for case in dataset.cases]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("Evaluation case IDs must be unique.")

    covered_categories: set[str] = set()
    covered_priorities: set[str] = set()
    covered_sentiments: set[str] = set()
    for case in dataset.cases:
        if case.expected_outcome == "provider_rejected":
            if case.provider_output_fixture is None:
                raise ValueError(
                    f"{case.case_id} must define a raw provider-output fixture."
                )
            if case.category != "malformed-provider-output":
                raise ValueError(
                    f"{case.case_id} provider rejection must use the malformed-provider-output category."
                )
            if case.semantic_expectations is not None:
                raise ValueError(
                    f"{case.case_id} cannot have semantic scores without a triage result."
                )
        else:
            if case.category == "malformed-provider-output":
                raise ValueError(
                    f"{case.case_id} malformed-provider-output case must be rejected."
                )
            if case.provider_output_fixture is not None:
                raise ValueError(
                    f"{case.case_id} has a provider fixture but does not expect provider rejection."
                )
            if case.semantic_expectations is None:
                raise ValueError(f"{case.case_id} must include semantic expectations.")
            if set(case.semantic_expectations) != {
                "response_quality",
                "rationale_quality",
                "safety_non_misleading_content",
            }:
                raise ValueError(
                    f"{case.case_id} must specify expectations for all semantic dimensions."
                )
            if set(case.expected.labels) != {
                "category",
                "priority",
                "sentiment",
                "department",
            }:
                raise ValueError(f"{case.case_id} must define all classification labels.")
            covered_categories.add(case.expected.labels["category"])
            covered_priorities.add(case.expected.labels["priority"])
            covered_sentiments.add(case.expected.labels["sentiment"])

        unknown_requirements = set(case.traceability.requirements) - ALLOWED_REQUIREMENTS
        unknown_invariants = set(case.traceability.invariants) - set(INVARIANTS)
        if unknown_requirements or unknown_invariants:
            raise ValueError(
                f"{case.case_id} has unknown traceability IDs: "
                f"{sorted(unknown_requirements | unknown_invariants)}"
            )
        if not any(item.startswith("SC-") for item in case.traceability.requirements):
            raise ValueError(f"{case.case_id} must link to at least one success criterion.")
        for invariant in case.traceability.invariants:
            if not set(INVARIANT_REQUIREMENTS[invariant]).intersection(
                case.traceability.requirements
            ):
                raise ValueError(
                    f"{case.case_id} does not link {invariant} to a relevant functional requirement."
                )
        if not case.message.strip():
            raise ValueError(
                f"{case.case_id} must use a valid customer message; blank input is a request test."
            )

    if covered_categories != EXPECTED_CATEGORIES:
        raise ValueError("Dataset must cover each supported category.")
    if covered_priorities != EXPECTED_PRIORITIES:
        raise ValueError("Dataset must cover each supported priority.")
    if covered_sentiments != EXPECTED_SENTIMENTS:
        raise ValueError("Dataset must cover each supported sentiment.")
    return dataset


def run_evaluation(
    *,
    phase: str = "final",
    human_decision: str | None = None,
    repair_actions: list[str] | None = None,
    dataset_path: Path = DEFAULT_DATASET,
    evidence_root: Path | None = None,
) -> dict[str, Any]:
    if phase not in {"initial", "final"}:
        raise ValueError("Evaluation phase must be initial or final.")
    if human_decision not in {None, "ACCEPT", "REJECT"}:
        raise ValueError("Human decision must be ACCEPT or REJECT.")

    settings = Settings.from_env()
    dataset = load_dataset(dataset_path)
    executions = _execute_cases(dataset.cases, settings)

    structural_cases = [
        evaluate_structural_case(
            item["case"],
            item["raw_provider_output"],
            item["result"],
            item["error_type"],
            item["persisted"],
        )
        for item in executions.values()
    ]
    structural_layer = aggregate_structural(structural_cases)

    behavioral_cases = [
        evaluate_behavioral_case(
            item["case"],
            item["result"],
            item["error_type"],
            item["persisted"],
        )
        for item in executions.values()
    ]
    empty_input_check = evaluate_empty_input_rejection()
    behavioral_layer = aggregate_behavioral(behavioral_cases, empty_input_check)

    result_map = {
        case_id: item["result"] for case_id, item in executions.items()
    }
    classification_layer = evaluate_classification(
        list(dataset.cases), result_map
    )
    semantic_layer = evaluate_semantics(list(dataset.cases), result_map, settings)
    system_layer = run_system_verification()

    layers = {
        "structural": structural_layer,
        "behavioral": behavioral_layer,
        "classification": classification_layer,
        "semantic": semantic_layer,
        "system_verification": system_layer,
    }
    final_status = overall_status([layer["status"] for layer in layers.values()])
    case_results = _combined_case_results(executions, layers)
    failures = [
        failure
        for layer in layers.values()
        for failure in layer.get("failure_details", [])
    ]
    semantic_config = semantic_layer.get("configuration", {})
    report: dict[str, Any] = {
        "runner_version": RUNNER_VERSION,
        "run_timestamp_utc": utc_now_iso(),
        "phase": phase,
        "overall_status": final_status,
        "thresholds": THRESHOLDS,
        "configuration": {
            "application_provider": "deterministic_mock_for_evaluation",
            "semantic_evaluator_model": semantic_config.get("model_configured"),
            "semantic_rubric_version": settings.semantic_rubric_version,
            "semantic_endpoint_configured": semantic_config.get("endpoint_configured", False),
            "semantic_credentials_configured": semantic_config.get(
                "credentials_configured", False
            ),
            "secrets_included": False,
        },
        "layers": layers,
        "case_results": case_results,
        "failure_details": failures,
        "repair_actions": repair_actions or [],
        "human_decision": human_decision or "PENDING",
    }
    output_root = evidence_root or ROOT / "evidence"
    write_evidence(report, executions, output_root)
    return report


def _execute_cases(
    cases: list[EvaluationCase], settings: Settings
) -> dict[str, dict[str, Any]]:
    with tempfile.TemporaryDirectory(prefix="triage-eval-cases-") as directory:
        case_settings = replace(
            settings,
            database_path=str(Path(directory) / "evaluation.sqlite3"),
            reviewer_credentials=(),
        )
        app = create_app(case_settings, provider=MockProvider())
        executions: dict[str, dict[str, Any]] = {}
        with TestClient(app) as client:
            repository: SQLiteRepository = app.state.repository
            for case in cases:
                before_count = repository.count_records()
                fixture = case.provider_output_fixture
                provider = MockProvider(
                    raw_response=fixture.raw_response if fixture else None
                )
                app.state.triage_service = TriageService(provider)
                response = client.post("/triage", json={"message": case.message})
                result: TriageResult | None = None
                error_type: str | None = None
                if response.status_code == 200:
                    try:
                        result = TriageResult.model_validate(response.json())
                    except (ValueError, TypeError):
                        error_type = "InvalidAPIResult"
                elif response.status_code == 503:
                    detail = response.json().get("detail", "")
                    error_type = (
                        "ProviderOutputError"
                        if "invalid output" in detail
                        else "ProviderUnavailable"
                    )
                else:
                    error_type = f"HTTP_{response.status_code}"
                executions[case.case_id] = {
                    "case": case,
                    "result": result,
                    "raw_provider_output": provider.last_response,
                    "error_type": error_type,
                    "persisted": repository.count_records() > before_count,
                    "http_status": response.status_code,
                }
    return executions


def run_system_verification() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="triage-system-check-") as directory:
        database_path = str(Path(directory) / "system-check.sqlite3")
        credentials = (
            ReviewerCredential("reviewer", "system-reviewer-token", "support-reviewer"),
            ReviewerCredential("agent", "system-agent-token", "support-agent"),
        )
        settings = Settings(
            database_path=database_path,
            triage_provider="mock",
            ai_base_url=None,
            ai_model=None,
            ai_api_key=None,
            ai_timeout_seconds=2.0,
            ai_max_retries=0,
            reviewer_credentials=credentials,
            semantic_base_url=None,
            semantic_model=None,
            semantic_api_key=None,
            semantic_timeout_seconds=2.0,
            semantic_rubric_version="1",
        )
        app = create_app(settings, provider=MockProvider())
        repository: SQLiteRepository = app.state.repository
        seed_result = TriageResult.model_validate(
            json.loads(MockProvider().triage("Thank you for the help."))
        )
        live_record_id = repository.create_record(
            "Thank you for the help.", seed_result
        )
        expired_record_id = repository.create_record(
            "This record has expired.",
            seed_result,
            created_at=datetime.now(UTC) - timedelta(days=31),
        )
        with TestClient(app) as client:
            authorized = client.get(
                f"/retained/{live_record_id}",
                headers={"Authorization": "Bearer system-reviewer-token"},
            )
            unauthenticated = client.get(f"/retained/{live_record_id}")
            unauthorized_role = client.get(
                f"/retained/{live_record_id}",
                headers={"Authorization": "Bearer system-agent-token"},
            )
            expired = client.get(
                f"/retained/{expired_record_id}",
                headers={"Authorization": "Bearer system-reviewer-token"},
            )
            expired_absent = not repository.record_exists(expired_record_id)

        checks = [
            _system_check(
                "SYS-001_AUTHORIZED_REVIEWER_ACCESS",
                authorized.status_code == 200,
                "support-reviewer can retrieve a retained record",
                authorized.status_code,
                ["FR-015", "SC-007", "BI-008"],
            ),
            _system_check(
                "SYS-002_UNAUTHENTICATED_DENIED",
                unauthenticated.status_code == 401,
                "unauthenticated access returns 401",
                unauthenticated.status_code,
                ["FR-015", "SC-007", "BI-008"],
            ),
            _system_check(
                "SYS-003_UNAUTHORIZED_ROLE_DENIED",
                unauthorized_role.status_code == 403,
                "authenticated user without support-reviewer role returns 403",
                unauthorized_role.status_code,
                ["FR-015", "SC-007", "BI-008"],
            ),
            _system_check(
                "SYS-004_EXPIRED_RECORD_DELETED",
                expired.status_code == 404 and expired_absent,
                "expired record returns 404 and is deleted",
                {
                    "status_code": expired.status_code,
                    "record_still_exists": not expired_absent,
                },
                ["FR-015", "SC-007", "BI-008"],
            ),
        ]
    failures = [
        {
            "case_id": check["check_id"],
            "input_message": None,
            "generated_output": check["actual_behavior"],
            "failed_requirement_or_invariant": check["traceability"],
            "failed_check": check["check_id"],
            "expected_behavior": check["expected_behavior"],
            "actual_behavior": check["actual_behavior"],
            "suggested_repair_area": "authentication, authorization, persistence, or retention",
        }
        for check in checks
        if check["outcome"] == FAIL
    ]
    return {
        "status": FAIL if failures else PASS,
        "metrics": {"checks_passed": len(checks) - len(failures), "checks_total": len(checks)},
        "checks": checks,
        "failure_details": failures,
    }


def write_evidence(
    report: dict[str, Any],
    executions: dict[str, dict[str, Any]],
    evidence_root: Path,
) -> None:
    write_json(evidence_root / "eval-results.json", report)
    phase_directory = evidence_root / f"{report['phase']}-generation"
    write_json(phase_directory / "evaluation-report.json", report)
    generated = {
        "phase": report["phase"],
        "run_timestamp_utc": report["run_timestamp_utc"],
        "provider": "deterministic_mock_for_evaluation",
        "case_outputs": [
            {
                "case_id": case_id,
                "input_message": item["case"].message,
                "raw_provider_output": item["raw_provider_output"],
                "triage_result": (
                    item["result"].model_dump(mode="json")
                    if item["result"] is not None
                    else None
                ),
                "provider_error": item["error_type"],
                "persisted": item["persisted"],
            }
            for case_id, item in executions.items()
        ],
    }
    write_json(
        phase_directory / "case-outputs.json",
        generated,
    )
    _append_harness_log(evidence_root / "harness-log.md", report)


def _append_harness_log(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    config = report["configuration"]
    lines = [
        f"## {report['phase'].title()} evaluation — {report['run_timestamp_utc']}",
        "",
        f"- Runner version: `{report['runner_version']}`",
        f"- Application provider: `{config['application_provider']}` (no credentials used)",
        f"- Semantic evaluator model: `{config['semantic_evaluator_model'] or 'NOT_CONFIGURED'}`",
        f"- Semantic rubric version: `{config['semantic_rubric_version']}`",
        "- Secrets recorded: no",
        f"- Overall result: **{report['overall_status']}**",
        "- Thresholds:",
    ]
    lines.extend(f"  - `{key}`: `{value}`" for key, value in report["thresholds"].items())
    lines.append("- Evaluation/system statuses:")
    lines.extend(
        f"  - `{name}`: **{layer['status']}**"
        for name, layer in report["layers"].items()
    )
    lines.append(f"- Meaningful failure records: {len(report['failure_details'])}")
    if report["failure_details"]:
        lines.append("- Failure details:")
        for failure in report["failure_details"]:
            lines.append(
                f"  - Case `{failure.get('case_id')}` — "
                f"`{failure.get('failed_check')}`: "
                f"expected `{json.dumps(failure.get('expected_behavior'), ensure_ascii=False)}`; "
                f"actual `{json.dumps(failure.get('actual_behavior'), ensure_ascii=False)}`; "
                f"repair area: {failure.get('suggested_repair_area')}."
            )
    semantic_reason = report["layers"]["semantic"].get("block_reason")
    if semantic_reason:
        lines.append(f"- Semantic evaluator limitation: {semantic_reason}")
    lines.extend(
        [
            "- Repair actions recorded in this run: "
            + (
                "; ".join(report["repair_actions"])
                if report["repair_actions"]
                else "none."
            ),
            f"- Human decision: **{report['human_decision']}**"
            + (
                " (reviewer decision required; the runner does not invent acceptance)."
                if report["human_decision"] == "PENDING"
                else "."
            ),
            "",
        ]
    )
    with path.open("a", encoding="utf-8") as log_file:
        log_file.write("\n".join(lines))


def _combined_case_results(
    executions: dict[str, dict[str, Any]], layers: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    structural = {
        item["case_id"]: item for item in layers["structural"]["case_results"]
    }
    behavioral = {
        item["case_id"]: item for item in layers["behavioral"]["case_results"]
    }
    semantic = {
        item["case_id"]: item for item in layers["semantic"].get("case_results", [])
    }
    combined: list[dict[str, Any]] = []
    for case_id, item in executions.items():
        case_statuses = [
            structural.get(case_id, {}).get("outcome", INCOMPLETE),
            behavioral.get(case_id, {}).get("outcome", INCOMPLETE),
        ]
        if item["case"].expected_outcome == "triage_result":
            case_statuses.append(
                semantic.get(case_id, {}).get(
                    "status", layers["semantic"]["status"]
                )
            )
        outcome = overall_status(case_statuses)
        combined.append(
            {
                "case_id": case_id,
                "outcome": outcome,
                "structural_observation": structural.get(case_id, {}).get(
                    "structural_observation"
                ),
                "triage_result": (
                    item["result"].model_dump(mode="json")
                    if item["result"] is not None
                    else None
                ),
                "provider_error": item["error_type"],
                "persisted": item["persisted"],
                "semantic_scores": semantic.get(case_id, {}).get("scores"),
            }
        )
    return combined


def _system_check(
    check_id: str,
    passed: bool,
    expected: str,
    actual: Any,
    traceability: list[str],
) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "outcome": PASS if passed else FAIL,
        "expected_behavior": expected,
        "actual_behavior": actual,
        "traceability": traceability,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run all triage evaluation layers.")
    parser.add_argument("--phase", choices=("initial", "final"), default="final")
    parser.add_argument("--human-decision", choices=("ACCEPT", "REJECT"))
    parser.add_argument(
        "--repair-action",
        action="append",
        default=[],
        help="Record a repair made before this run; may be supplied more than once.",
    )
    arguments = parser.parse_args(argv)
    report = run_evaluation(
        phase=arguments.phase,
        human_decision=arguments.human_decision,
        repair_actions=arguments.repair_action,
    )
    print(
        json.dumps(
            {
                "overall_status": report["overall_status"],
                "layers": {
                    name: layer["status"] for name, layer in report["layers"].items()
                },
                "report_path": str(ROOT / "evidence" / "eval-results.json"),
            },
            indent=2,
        )
    )
    return 0 if report["overall_status"] == PASS else 1


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    raise SystemExit(main())
