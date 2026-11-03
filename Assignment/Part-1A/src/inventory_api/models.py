"""Validated API request and response models."""

from __future__ import annotations

import math
from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ItemFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    category: str = Field(min_length=1)
    quantity: float = Field(ge=0, allow_inf_nan=False)
    unit_price: float = Field(ge=0, allow_inf_nan=False)
    expiry_date: date | None = None

    @field_validator("name", "category", mode="before")
    @classmethod
    def strip_required_text(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()
        return value


    @field_validator("name", "category")
    @classmethod
    def require_nonempty_text(cls, value: str) -> str:
        if not value:
            raise ValueError("must not be empty")
        return value

    @field_validator("quantity", "unit_price", mode="before")
    @classmethod
    def validate_finite_number(cls, value: Any) -> Any:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("must be a finite non-negative number")  # noqa: TRY004
        try:
            numeric_value = float(value)
        except (OverflowError, TypeError, ValueError) as exc:
            raise ValueError("must be a finite non-negative number") from exc
        if not math.isfinite(numeric_value):
            raise ValueError("must be a finite non-negative number")
        return numeric_value

    @field_validator("expiry_date", mode="before")
    @classmethod
    def validate_expiry_date(cls, value: Any) -> Any:
        if value is None:
            return value
        if isinstance(value, date):
            return value
        if not isinstance(value, str):
            raise ValueError("must be a date in YYYY-MM-DD format or null")  # noqa: TRY004
        try:
            parsed = date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("must be a date in YYYY-MM-DD format or null") from exc
        if parsed.isoformat() != value:
            raise ValueError("must be a date in YYYY-MM-DD format or null")
        return parsed


class ItemCreate(ItemFields):
    id: str = Field(min_length=1)

    @field_validator("id", mode="before")
    @classmethod
    def strip_identifier(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("id")
    @classmethod
    def require_nonempty_identifier(cls, value: str) -> str:
        if not value:
            raise ValueError("must not be empty")
        return value


class ItemUpdate(ItemFields):
    pass


class ItemResponse(ItemFields):
    id: str = Field(min_length=1)
    currency: str = Field(min_length=3, max_length=3)


class ErrorResponse(BaseModel):
    detail: str
