from __future__ import annotations

import time
from pathlib import Path

import httpx

from src.config import Settings
from src.providers.base import ProviderUnavailable


class ConfiguredProvider:
    def __init__(self, settings: Settings):
        self.settings = settings
        prompt_path = Path(__file__).resolve().parents[2] / "prompts" / "triage.txt"
        self.system_prompt = prompt_path.read_text(encoding="utf-8")

    def triage(self, message: str) -> str:
        if not all(
            (self.settings.ai_base_url, self.settings.ai_model, self.settings.ai_api_key)
        ):
            raise ProviderUnavailable("The configured application AI provider is unavailable.")

        endpoint = self.settings.ai_base_url.rstrip("/") + "/chat/completions"
        headers = {"Authorization": f"Bearer {self.settings.ai_api_key}"}
        payload = {
            "model": self.settings.ai_model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": message},
            ],
        }
        last_error: Exception | None = None
        for attempt in range(self.settings.ai_max_retries + 1):
            try:
                with httpx.Client(timeout=self.settings.ai_timeout_seconds) as client:
                    response = client.post(endpoint, headers=headers, json=payload)
                if response.status_code == 429 or response.status_code >= 500:
                    response.raise_for_status()
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                if isinstance(content, str) and content:
                    return content
                raise ProviderUnavailable(
                    "The configured application AI provider returned no text."
                )
            except httpx.TimeoutException as exc:
                last_error = exc
            except httpx.TransportError as exc:
                last_error = exc
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code < 500 and exc.response.status_code != 429:
                    raise ProviderUnavailable(
                        "The configured application AI provider rejected the request."
                    ) from exc
                last_error = exc
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                raise ProviderUnavailable(
                    "The configured application AI provider returned an invalid response."
                ) from exc
            if attempt < self.settings.ai_max_retries:
                time.sleep(min(0.25 * (2**attempt), 1.0))
        raise ProviderUnavailable(
            "The configured application AI provider is unavailable."
        ) from last_error
