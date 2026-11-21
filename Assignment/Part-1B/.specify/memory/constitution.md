<!--
Sync Impact Report
Version change: uninitialized template -> 1.0.0
Modified principles: established five core principles for this project
Added sections: Additional Constraints; Development Workflow and Quality Gates
Removed sections: none
Follow-up TODOs: none
-->

# Part-1B Project Constitution

## Core Principles

### I. Requirements-First Development
Every feature MUST begin with clear user needs, functional requirements, and verifiable
acceptance criteria. Specifications MUST be clarified before implementation when a material
behavior or constraint is ambiguous. Design, implementation, and tests MUST remain traceable to
those requirements.

### II. Simple, Modular Design
Solutions MUST use the simplest architecture that satisfies approved requirements. Components
MUST have clear responsibilities and interfaces. New dependencies, abstractions, and configuration
MUST be justified by concrete needs; unrelated refactoring MUST NOT be bundled with feature work.

### III. Verified Delivery
Changes MUST include automated tests appropriate to their behavior and risk. Tests MUST be
deterministic, isolated from external services unless explicitly required, and assert meaningful
outcomes rather than implementation details. Relevant tests and configured lint or type checks
MUST pass before a change is considered complete; known failures MUST be reported.

### IV. Security and Privacy by Design
Inputs MUST be validated at trust boundaries, and persistence or external commands MUST use safe,
structured APIs rather than unsafe string construction. Secrets and unnecessary personal data
MUST NOT be committed or exposed in logs, examples, or test fixtures. Access and data handling
MUST remain within the approved project scope.

### V. Responsible AI and Maintainability
AI-assisted specifications, code, tests, and documentation MUST be reviewed by a human for
correctness, security, requirement fit, and maintainability. Material claims MUST be supported by
repository evidence or verification results. Code and documentation MUST be clear enough for
another project contributor to understand and maintain.

## Additional Constraints
Implementation MUST follow the technology, platform, and dependency decisions recorded in the
approved specification and plan. A change to those decisions MUST include an explicit rationale
and an assessment of its effect on existing requirements and tests. The project MUST remain within
its agreed assignment scope; optional features MUST NOT replace required behavior.

## Development Workflow and Quality Gates
Work MUST proceed through a traceable specification, plan, task breakdown, implementation, and
verification appropriate to the change. Tasks MUST identify affected files and meaningful
dependencies. Before completion, contributors MUST check relevant acceptance criteria, run the
smallest sufficient automated test and quality-check commands, and update directly related
documentation. Any intentional deviation from this constitution MUST be documented with its
rationale and impact.

## Governance
This constitution governs project decisions and takes precedence over conflicting project
guidance. Amendments MUST be deliberate, recorded in version control, and reviewed for impacts on
specifications, plans, tasks, tests, and contributor guidance. Versioning follows semantic
versioning: PATCH for non-semantic clarification, MINOR for additive principles or requirements,
and MAJOR for incompatible changes to existing principles. Contributors MUST review changes for
compliance with these principles; any exception requires explicit rationale and approval from the
project owner.

**Version**: 1.0.0 | **Ratified**: 2026-11-02 | **Last Amended**: 2026-11-03
