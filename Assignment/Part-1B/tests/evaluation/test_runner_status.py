import json

import pytest

from src.config import Settings
from src.domain.triage import TriageService
from src.evaluation.report import BLOCKED, FAIL, INCOMPLETE, PASS, overall_status
from src.evaluation.runner import load_dataset, run_evaluation, run_system_verification
from src.evaluation.semantic_evaluator import evaluate_semantics
from src.providers.mock_provider import MockProvider


def test_overall_status_requires_all_mandatory_results_to_pass():
    assert overall_status([PASS, PASS]) == PASS
    assert overall_status([PASS, FAIL]) == FAIL
    assert overall_status([PASS, BLOCKED]) == BLOCKED
    assert overall_status([PASS, INCOMPLETE]) == INCOMPLETE
    assert overall_status([FAIL, BLOCKED]) == FAIL


def test_semantic_rubric_version_cannot_be_changed(monkeypatch):
    monkeypatch.setenv("SEMANTIC_EVALUATOR_RUBRIC_VERSION", "2")
    with pytest.raises(ValueError, match="fixed rubric version"):
        Settings.from_env()


def test_missing_semantic_evaluator_is_blocked(make_settings):
    dataset = load_dataset()
    case = dataset.cases[0]
    output = TriageService(MockProvider()).triage(case.message)
    settings = make_settings()
    layer = evaluate_semantics([case], {case.case_id: output}, settings)
    assert layer["status"] == BLOCKED
    assert layer["case_results"] == []


def test_invalid_semantic_response_is_incomplete(monkeypatch, make_settings):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "model": "fixed-test-model",
                "choices": [{"message": {"content": json.dumps({"wrong": "shape"})}}],
            }

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return None

        def post(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr("src.evaluation.semantic_evaluator.httpx.Client", FakeClient)
    dataset = load_dataset()
    case = dataset.cases[0]
    output = TriageService(MockProvider()).triage(case.message)
    settings = make_settings(
        semantic_base_url="https://example.invalid/v1",
        semantic_model="fixed-test-model",
        semantic_api_key="test-key",
    )
    layer = evaluate_semantics([case], {case.case_id: output}, settings)
    assert layer["status"] == INCOMPLETE
    assert layer["case_results"] == []


def test_valid_semantic_response_records_scores_and_fixed_model(monkeypatch, make_settings):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            scores = {
                dimension: {"score": 5, "reason": "The result is grounded and safe."}
                for dimension in (
                    "response_quality",
                    "rationale_quality",
                    "safety_non_misleading_content",
                )
            }
            return {
                "model": "fixed-test-model",
                "choices": [{"message": {"content": json.dumps(scores)}}],
            }

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return None

        def post(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr("src.evaluation.semantic_evaluator.httpx.Client", FakeClient)
    case = load_dataset().cases[0]
    output = TriageService(MockProvider()).triage(case.message)
    settings = make_settings(
        semantic_base_url="https://example.invalid/v1",
        semantic_model="fixed-test-model",
        semantic_api_key="test-key",
    )
    layer = evaluate_semantics([case], {case.case_id: output}, settings)
    assert layer["status"] == PASS
    assert layer["metrics"]["means"]["response_quality"] == 5
    assert layer["configuration"]["model_reported"] == "fixed-test-model"


def test_system_level_authentication_and_retention_checks_pass():
    result = run_system_verification()
    assert result["status"] == PASS
    assert result["metrics"]["checks_passed"] == 4


def test_runner_reports_blocked_semantics_without_overall_pass(
    monkeypatch, tmp_path
):
    for name in (
        "SEMANTIC_EVALUATOR_BASE_URL",
        "SEMANTIC_EVALUATOR_MODEL",
        "SEMANTIC_EVALUATOR_API_KEY",
    ):
        monkeypatch.setenv(name, "")
    report = run_evaluation(
        phase="final",
        repair_actions=["Corrected deterministic mock case matching."],
        evidence_root=tmp_path / "evidence",
    )
    assert report["layers"]["semantic"]["status"] == BLOCKED
    assert report["overall_status"] == BLOCKED
    assert report["human_decision"] == "PENDING"
    assert report["repair_actions"] == ["Corrected deterministic mock case matching."]
    malformed_case = next(
        item
        for item in report["case_results"]
        if item["case_id"] == "malformed-provider-response"
    )
    assert malformed_case["outcome"] == PASS
    assert malformed_case["structural_observation"]["valid"] is False
    assert malformed_case["persisted"] is False
    successful_case = next(
        item
        for item in report["case_results"]
        if item["case_id"] == "payment-duplicate-charge"
    )
    assert successful_case["outcome"] == BLOCKED
    assert successful_case["persisted"] is True
    assert (tmp_path / "evidence" / "eval-results.json").is_file()
    harness_log = (tmp_path / "evidence" / "harness-log.md").read_text(
        encoding="utf-8"
    )
    assert "Corrected deterministic mock case matching." in harness_log
