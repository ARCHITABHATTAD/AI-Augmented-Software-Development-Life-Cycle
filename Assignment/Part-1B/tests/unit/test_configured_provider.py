from dataclasses import replace

import httpx
import pytest

from src.providers.base import ProviderUnavailable
from src.providers.configured_provider import ConfiguredProvider


def test_configured_provider_uses_env_settings_and_returns_raw_text(
    monkeypatch, make_settings
):
    observed = {}

    class FakeClient:
        def __init__(self, **kwargs):
            observed["timeout"] = kwargs["timeout"]

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return None

        def post(self, url, *, headers, json):
            observed.update({"url": url, "headers": headers, "payload": json})
            request = httpx.Request("POST", url)
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": '{"category":"GENERAL"}'}}]},
                request=request,
            )

    monkeypatch.setattr("src.providers.configured_provider.httpx.Client", FakeClient)
    settings = replace(
        make_settings(),
        ai_base_url="https://provider.example/v1",
        ai_model="triage-model-v1",
        ai_api_key="test-key",
    )
    output = ConfiguredProvider(settings).triage("Please help.")
    assert output == '{"category":"GENERAL"}'
    assert observed["url"] == "https://provider.example/v1/chat/completions"
    assert observed["payload"]["model"] == "triage-model-v1"
    assert observed["headers"]["Authorization"] == "Bearer test-key"


def test_configured_provider_without_credentials_is_explicitly_unavailable(make_settings):
    with pytest.raises(ProviderUnavailable):
        ConfiguredProvider(make_settings()).triage("A valid customer message.")
