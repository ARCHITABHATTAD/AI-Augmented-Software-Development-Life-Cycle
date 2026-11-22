from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ProviderOutputFixture(BaseModel):
    model_config = ConfigDict(extra="forbid")

    adapter: Literal["deterministic_fake"]
    raw_response: str


class ExpectedCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    labels: dict[str, str]
    behavioral_assertions: dict[str, bool]


class CaseTraceability(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requirements: list[str] = Field(min_length=1)
    invariants: list[str] = Field(min_length=1)


class EvaluationCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    message: str = Field(min_length=1)
    expected_outcome: Literal["triage_result", "provider_rejected"]
    expected: ExpectedCase
    semantic_expectations: dict[str, str] | None
    traceability: CaseTraceability
    provider_output_fixture: ProviderOutputFixture | None = None


class EvaluationDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_version: int
    cases: list[EvaluationCase] = Field(min_length=15)
