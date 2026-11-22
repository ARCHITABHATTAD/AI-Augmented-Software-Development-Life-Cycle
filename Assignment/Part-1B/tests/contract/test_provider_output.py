import json

import pytest

from src.domain.validation import ProviderOutputError, validate_provider_output
from tests.contract.test_triage_contract import valid_result


@pytest.mark.parametrize(
    "output",
    [
        "not json",
        "Here is the result: {}",
        "[]",
        json.dumps({**valid_result(), "extra": "not allowed"}),
        json.dumps({**valid_result(), "category": "UNKNOWN"}),
        json.dumps({**valid_result(), "clarification_required": True}),
    ],
)
def test_invalid_provider_output_is_rejected(output):
    with pytest.raises(ProviderOutputError):
        validate_provider_output(output)
