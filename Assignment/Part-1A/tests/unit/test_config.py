import pytest

from inventory_api.config import Settings


def test_settings_use_local_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("INVENTORY_DB_PATH", raising=False)
    monkeypatch.delenv("LOW_STOCK_THRESHOLD", raising=False)
    monkeypatch.delenv("INVENTORY_CURRENCY", raising=False)

    settings = Settings.from_env()

    assert settings.database_path.as_posix() == "data/inventory.sqlite3"
    assert settings.low_stock_threshold == 1
    assert settings.currency == "INR"


def test_settings_parse_configured_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INVENTORY_DB_PATH", "custom/inventory.sqlite3")
    monkeypatch.setenv("LOW_STOCK_THRESHOLD", "0.75")
    monkeypatch.setenv("INVENTORY_CURRENCY", "usd")

    settings = Settings.from_env()

    assert settings.database_path.as_posix() == "custom/inventory.sqlite3"
    assert settings.low_stock_threshold == 0.75
    assert settings.currency == "USD"


@pytest.mark.parametrize("value", ["not-a-number", "-1", "nan", "inf", "-inf"])
def test_settings_reject_invalid_threshold(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("LOW_STOCK_THRESHOLD", value)

    with pytest.raises(ValueError, match="LOW_STOCK_THRESHOLD"):
        Settings.from_env()


@pytest.mark.parametrize("value", ["", "US", "USDD", "12$"])
def test_settings_reject_invalid_currency_format(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("INVENTORY_CURRENCY", value)

    with pytest.raises(ValueError, match="INVENTORY_CURRENCY"):
        Settings.from_env()
