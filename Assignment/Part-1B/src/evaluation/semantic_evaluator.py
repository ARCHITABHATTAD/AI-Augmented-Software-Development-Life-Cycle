
from __future__ import annotations

import json
import time
from pathlib import Path
from statistics import mean
from typing import Any

import httpx

from src.config import Settings
from src.domain.triage import TriageResult
from src.evaluation.models import EvaluationCase
from src.evaluation.report import (
    BLOCKED,
    FAIL,
    INCOMPLETE,
    PASS,
    THRESHOLDS,
    new_failure,
)

DIMENSIONS = (
    "response_quality",
    "rationale_quality",
    "safety_non_misleading_content",
)
PROMPT_PATH = (
    Path(__file__).resolve().parents[2] / "prompts" / "semantic-evaluation.txt"
)


def evaluate_semantics(
    cases: list[EvaluationCase],
    outputs: dict[str, TriageResult | None],
    settings: Settings,
) -> dict[str, Any]:
    if not all(
        (settings.semantic_base_url, settings.semantic_model, settings.semantic_api_key)
    ):
        return {
            "status": BLOCKED,
            "metrics": {},
            "case_results": [],
            "failure_details": [],
            "block_reason": (
                "Semantic evaluator model, endpoint, or credentials are not configured."
            ),
            "configuration": _configuration(settings),
        }

    eligible = [
        case for case in cases if case.expected_outcome == "triage_result"
    ]

    if not eligible or any(
        outputs.get(case.case_id) is None for case in eligible
    ):
        return {
            "status": INCOMPLETE,
            "metrics": {},
            "case_results": [],
            "failure_details": [],
            "block_reason": (
                "One or more triage outputs required for semantic scoring are missing."
            ),
            "configuration": _configuration(settings),
        }

    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
    endpoint = settings.semantic_base_url.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {settings.semantic_api_key}"}

    scored: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    actual_model = None

    for case in eligible:
        result = outputs[case.case_id]
        assert result is not None

        request_payload = {
            "case_id": case.case_id,
            "message": case.message,
            "reviewed_expectations": case.expected.model_dump(mode="json"),
            "semantic_expectations": case.semantic_expectations,
            "triage_output": result.model_dump(mode="json"),
        }

        if scored:
            time.sleep(15)

        try:
            with httpx.Client(
                timeout=settings.semantic_timeout_seconds
            ) as client:
                response = client.post(
                    endpoint,
                    headers=headers,
                    json={
                        "model": settings.semantic_model,
                        "temperature": 0,
                        "response_format": {"type": "json_object"},
                        "messages": [
                            {
                                "role": "system",
                                "content": system_prompt,
                            },
                            {
                                "role": "user",
                                "content": json.dumps(
                                    request_payload,
                                    ensure_ascii=False,
                                ),
                            },
                        ],
                    },
                )
                response.raise_for_status()

        except httpx.HTTPStatusError as exc:
            error_code = None

            try:
                error_data = exc.response.json()

                if isinstance(error_data, dict):
                    error = error_data.get("error", {})

                    if isinstance(error, dict):
                        error_code = error.get("code") or error.get("type")

            except ValueError:
                pass

            retry_after = exc.response.headers.get("retry-after")

            return {
                "status": BLOCKED,
                "metrics": _semantic_metrics(scored),
                "case_results": scored,
                "failure_details": failures,
                "block_reason": (
                    f"Semantic evaluator request failed "
                    f"(HTTP {exc.response.status_code}; "
                    f"code={error_code or 'not provided'}; "
                    f"retry_after={retry_after or 'not provided'})."
                ),
                "configuration": _configuration(
                    settings,
                    actual_model=actual_model,
                ),
            }

        except (httpx.TimeoutException, httpx.TransportError) as exc:
            return {
                "status": BLOCKED,
                "metrics": _semantic_metrics(scored),
                "case_results": scored,
                "failure_details": failures,
                "block_reason": (
                    f"Semantic evaluator request failed ({type(exc).__name__})."
                ),
                "configuration": _configuration(
                    settings,
                    actual_model=actual_model,
                ),
            }

        try:
            response_data = response.json()

            if not isinstance(response_data, dict):
                raise TypeError(
                    "Semantic evaluator response must be an object."
                )

            actual_model = response_data.get("model")
            content = response_data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            scores = _validate_scores(parsed)

        except (ValueError, KeyError, IndexError, TypeError) as exc:
            return {
                "status": INCOMPLETE,
                "metrics": _semantic_metrics(scored),
                "case_results": scored,
                "failure_details": failures,
                "block_reason": (
                    "Semantic evaluator returned invalid or incomplete output: "
                    f"{type(exc).__name__}: {exc}"
                ),
                "configuration": _configuration(
                    settings,
                    actual_model=actual_model,
                ),
            }

        if actual_model != settings.semantic_model:
            return {
                "status": INCOMPLETE,
                "metrics": _semantic_metrics(scored),
                "case_results": scored,
                "failure_details": failures,
                "block_reason": (
                    "Semantic evaluator response model is missing or differs "
                    "from configured model."
                ),
                "configuration": _configuration(
                    settings,
                    actual_model=actual_model,
                ),
            }

        safety_score = scores["safety_non_misleading_content"]["score"]

        safety_floor_applies = bool(
            set(case.traceability.requirements).intersection(
                {"FR-009", "FR-010"}
            )
        )

        scored_case = {
            "case_id": case.case_id,
            "scores": scores,
            "status": (
                FAIL
                if safety_floor_applies
                and safety_score
                < THRESHOLDS["security_prohibited_safety_minimum"]
                else PASS
            ),
        }

        scored.append(scored_case)

        for dimension in DIMENSIONS:
            if scores[dimension]["score"] < 1:
                failures.append(
                    new_failure(
                        case_id=case.case_id,
                        message=case.message,
                        output=result.model_dump(mode="json"),
                        check=f"SEMANTIC_{dimension.upper()}_RANGE",
                        expected=(
                            "integer score from 1 to 5 with a brief reason"
                        ),
                        actual=scores[dimension],
                        suggested_repair_area=(
                            "triage output quality and fixed semantic rubric"
                        ),
                        requirements=case.traceability.requirements,
                        invariants=case.traceability.invariants,
                    )
                )

    metrics = _semantic_metrics(scored)
    threshold_failures: list[dict[str, Any]] = []

    for dimension, average in metrics["means"].items():
        if average < THRESHOLDS["semantic_mean_per_dimension"]:
            threshold_failures.append(
                {
                    "case_id": None,
                    "input_message": None,
                    "generated_output": None,
                    "failed_requirement_or_invariant": [
                        "FR-013",
                        "FR-014",
                        "SC-005",
                    ],
                    "failed_check": f"SEMANTIC_{dimension.upper()}_MEAN",
                    "expected_behavior": (
                        THRESHOLDS["semantic_mean_per_dimension"]
                    ),
                    "actual_behavior": average,
                    "suggested_repair_area": (
                        "triage output quality; do not lower rubric thresholds"
                    ),
                }
            )

    safety_floor = THRESHOLDS["security_prohibited_safety_minimum"]

    for case in eligible:
        if not set(case.traceability.requirements).intersection(
            {"FR-009", "FR-010"}
        ):
            continue

        case_scores = next(
            item["scores"]
            for item in scored
            if item["case_id"] == case.case_id
        )

        actual_score = case_scores["safety_non_misleading_content"]["score"]

        if actual_score < safety_floor:
            threshold_failures.append(
                {
                    "case_id": case.case_id,
                    "input_message": case.message,
                    "generated_output": outputs[
                        case.case_id
                    ].model_dump(mode="json"),
                    "failed_requirement_or_invariant": [
                        *case.traceability.requirements,
                        *case.traceability.invariants,
                    ],
                    "failed_check": (
                        "SEMANTIC_SECURITY_PROHIBITED_SAFETY_FLOOR"
                    ),
                    "expected_behavior": (
                        f"safety score at least {safety_floor}"
                    ),
                    "actual_behavior": actual_score,
                    "suggested_repair_area": (
                        "safety response and human-review handling"
                    ),
                }
            )

    failures.extend(threshold_failures)

    return {
        "status": FAIL if failures else PASS,
        "metrics": metrics,
        "case_results": scored,
        "failure_details": failures,
        "configuration": _configuration(
            settings,
            actual_model=actual_model,
        ),
    }


def _validate_scores(value: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(value, dict) or set(value) != set(DIMENSIONS):
        raise ValueError(
            "Semantic evaluator must return exactly the three rubric dimensions."
        )

    scores: dict[str, dict[str, Any]] = {}

    for dimension in DIMENSIONS:
        item = value[dimension]

        if not isinstance(item, dict) or set(item) != {"score", "reason"}:
            raise ValueError(
                "Each semantic dimension must contain score and reason."
            )

        score = item["score"]
        reason = item["reason"]

        if type(score) is not int or not 1 <= score <= 5:
            raise ValueError(
                "Semantic scores must be integers from 1 through 5."
            )

        if not isinstance(reason, str) or not reason.strip():
            raise ValueError(
                "Each semantic score must have a brief reason."
            )

        scores[dimension] = {
            "score": score,
            "reason": reason.strip(),
        }

    return scores


def _semantic_metrics(
    scored: list[dict[str, Any]],
) -> dict[str, Any]:
    means = {
        dimension: (
            mean(
                item["scores"][dimension]["score"]
                for item in scored
            )
            if scored
            else None
        )
        for dimension in DIMENSIONS
    }

    return {
        "means": means,
        "cases_scored": len(scored),
    }


def _configuration(
    settings: Settings,
    actual_model: str | None = None,
) -> dict[str, str | None]:
    return {
        "model_configured": settings.semantic_model,
        "model_reported": actual_model,
        "rubric_version": settings.semantic_rubric_version,
        "endpoint_configured": bool(settings.semantic_base_url),
        "credentials_configured": bool(settings.semantic_api_key),
    }
