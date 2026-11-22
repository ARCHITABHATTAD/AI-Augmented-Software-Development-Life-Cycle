from typing import Protocol


class ProviderUnavailable(RuntimeError):
    pass


class AIProvider(Protocol):
    def triage(self, message: str) -> str:
        """Return the provider's raw JSON response text."""
