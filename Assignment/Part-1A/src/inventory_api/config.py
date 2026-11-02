"""Startup configuration for the inventory service."""

from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass
from pathlib import Path



@dataclass(frozen=True)
class Settings:
    database_path: Path
    low_stock_threshold: float
    currency: str

    @classmethod
    def from_env(cls) -> Settings:
        database_path = Path(os.getenv("INVENTORY_DB_PATH", "data/inventory.sqlite3"))

        threshold_value = os.getenv("LOW_STOCK_THRESHOLD", "1")
        try:
            low_stock_threshold = float(threshold_value)
        except ValueError as exc:
            raise ValueError("LOW_STOCK_THRESHOLD must be a finite non-negative number") from exc
        if not math.isfinite(low_stock_threshold) or low_stock_threshold < 0:
            raise ValueError("LOW_STOCK_THRESHOLD must be a finite non-negative number")

        currency = os.getenv("INVENTORY_CURRENCY", "INR").strip().upper()
        if re.fullmatch(r"[A-Z]{3}", currency, flags=re.ASCII) is None:
            raise ValueError("INVENTORY_CURRENCY must be a three-letter ISO 4217 code")

        return cls(
            database_path=database_path,
            low_stock_threshold=low_stock_threshold,
            currency=currency,
        )
