INVARIANTS = {
    "BI-001": "Allowed classification values and category-to-department mapping",
    "BI-002": "Clarification is focused and only required when material",
    "BI-003": "Security-sensitive cases require human review and do not repeat secrets",
    "BI-004": "Prohibited transactions/account modifications are not claimed as completed",
    "BI-005": "Multiple issues receive one dominant classification",
    "BI-006": "Invalid provider output is rejected without persisting a result",
    "BI-007": "Empty input is rejected before provider invocation or persistence",
    "BI-008": "Retained-record access requires the support-reviewer role and expiration",
}

INVARIANT_REQUIREMENTS = {
    "BI-001": ["FR-002", "FR-003", "FR-004", "FR-005", "FR-007"],
    "BI-002": ["FR-008"],
    "BI-003": ["FR-009"],
    "BI-004": ["FR-010"],
    "BI-005": ["FR-002"],
    "BI-006": ["FR-007", "FR-013"],
    "BI-007": ["FR-001"],
    "BI-008": ["FR-015"],
}
