from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv

FIXED_SEMANTIC_RUBRIC_VERSION = "1"


@dataclass(frozen=True)
class ReviewerCredential:
    username: str
    token: str
    role: str


@dataclass(frozen=True)
class Settings:
    database_path: str
    triage_provider: str
    ai_base_url: str | None
    ai_model: str | None
    ai_api_key: str | None
    ai_timeout_seconds: float
    ai_max_retries: int
    reviewer_credentials: tuple[ReviewerCredential, ...]
    semantic_base_url: str | None
    semantic_model: str | None
    semantic_api_key: str | None
    semantic_timeout_seconds: float
    semantic_rubric_version: str

    @classmethod
    def from_env(cls) -> Settings:
        load_dotenv()
        rubric_version = os.getenv(
            "SEMANTIC_EVALUATOR_RUBRIC_VERSION", FIXED_SEMANTIC_RUBRIC_VERSION
        )
        if rubric_version != FIXED_SEMANTIC_RUBRIC_VERSION:
            raise ValueError(
                "SEMANTIC_EVALUATOR_RUBRIC_VERSION must match the fixed rubric version."
            )
        raw_credentials = os.getenv("REVIEWER_CREDENTIALS_JSON", "[]")
        try:
            credentials_data: Any = json.loads(raw_credentials)
        except json.JSONDecodeError as exc:
            raise ValueError("REVIEWER_CREDENTIALS_JSON must be valid JSON.") from exc
        if not isinstance(credentials_data, list):
            raise TypeError("REVIEWER_CREDENTIALS_JSON must contain a JSON array.")

        credentials: list[ReviewerCredential] = []
        for item in credentials_data:
            if not isinstance(item, dict) or not all(
                isinstance(item.get(key), str) and item[key]
                for key in ("username", "token", "role")
            ):
                raise ValueError(
                    "Each reviewer credential must contain non-empty username, token, and role."
                )
            credentials.append(
                ReviewerCredential(
                    username=item["username"],
                    token=item["token"],
                    role=item["role"],
                )
            )

        return cls(
            database_path=os.getenv("DATABASE_PATH", "./data/triage.sqlite3"),
            triage_provider=os.getenv("TRIAGE_PROVIDER", "mock").strip().lower(),
            ai_base_url=os.getenv("AI_BASE_URL") or None,
            ai_model=os.getenv("AI_MODEL") or None,
            ai_api_key=os.getenv("AI_API_KEY") or None,
            ai_timeout_seconds=_positive_float("AI_TIMEOUT_SECONDS", 20.0),
            ai_max_retries=_bounded_int("AI_MAX_RETRIES", 2, 0, 5),
            reviewer_credentials=tuple(credentials),
            semantic_base_url=os.getenv("SEMANTIC_EVALUATOR_BASE_URL") or None,
            semantic_model=os.getenv("SEMANTIC_EVALUATOR_MODEL") or None,
            semantic_api_key=os.getenv("SEMANTIC_EVALUATOR_API_KEY") or None,
            semantic_timeout_seconds=_positive_float(
                "SEMANTIC_EVALUATOR_TIMEOUT_SECONDS", 30.0
            ),
            semantic_rubric_version=rubric_version,
        )


def _positive_float(name: str, default: float) -> float:
    value = float(os.getenv(name, str(default)))
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero.")
    return value


def _bounded_int(name: str, default: int, minimum: int, maximum: int) -> int:
    value = int(os.getenv(name, str(default)))
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}.")
    return value
