from src.evaluation.invariants import INVARIANTS
from src.evaluation.runner import load_dataset


def test_dataset_has_at_least_15_traceable_cases_and_all_labels():
    dataset = load_dataset()
    assert len(dataset.cases) >= 15
    assert len({case.case_id for case in dataset.cases}) == len(dataset.cases)
    for case in dataset.cases:
        assert case.traceability.requirements
        assert case.traceability.invariants
        assert set(case.traceability.invariants) <= set(INVARIANTS)
        assert any(item.startswith("SC-") for item in case.traceability.requirements)


def test_malformed_provider_fixture_is_valid_input_and_bypasses_live_model():
    dataset = load_dataset()
    case = next(case for case in dataset.cases if case.expected_outcome == "provider_rejected")
    assert case.message.strip()
    assert case.category == "malformed-provider-output"
    assert case.provider_output_fixture is not None
    assert case.provider_output_fixture.adapter == "deterministic_fake"
    assert case.semantic_expectations is None


def test_every_output_case_has_all_semantic_expectation_dimensions():
    dataset = load_dataset()
    expected_dimensions = {
        "response_quality",
        "rationale_quality",
        "safety_non_misleading_content",
    }
    for case in dataset.cases:
        if case.expected_outcome == "triage_result":
            assert set(case.semantic_expectations) == expected_dimensions
