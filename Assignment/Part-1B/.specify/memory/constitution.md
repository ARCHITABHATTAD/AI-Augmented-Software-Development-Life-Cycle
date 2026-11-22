<!--
Sync Impact Report
Version change: uninitialized -> 1.0.0 (initial adoption)
Modified principles: template placeholders -> Requirements Before Implementation;
  Simple, Modular Design; Verified Delivery; Security and Privacy by Design;
  Responsible AI Assistance
Added sections: Engineering Constraints; Development Workflow and Quality Gates
Removed sections: none
Follow-up TODOs: none
-->

# AI-Augmented Software Development Life Cycle - Part 1B Constitution

## Core Principles

### I. Requirements Before Implementation
Every change MUST trace to a stated user need or assignment requirement. Before implementation,
record its scope, observable acceptance criteria, and relevant constraints in the specification.
Resolve ambiguity before coding; changes to scope MUST be reflected in the specification.

### II. Simple, Modular Design
Design MUST favor small, cohesive components and clear interfaces that fit established project
patterns. Reuse existing capabilities where suitable; new dependencies, abstractions, and
configuration MUST be justified by a concrete requirement. Avoid speculative features and
unnecessary complexity.

### III. Verified Delivery
Behavioral changes MUST have automated tests at the appropriate unit, integration, or end-to-end
level. Tests MUST cover the acceptance criteria and relevant regressions. Before declaring work
complete, run the focused tests and applicable project checks; report any checks that could not be
run and why.

### IV. Security and Privacy by Design
Input MUST be validated at trust boundaries, access MUST be limited to what is needed, and secrets
MUST be kept out of source control, prompts, and logs. Changes that handle user data MUST minimize
collection and exposure. Security- or privacy-relevant behavior MUST be included in review and
testing.

### V. Responsible AI Assistance
AI-generated code, specifications, and analysis are proposals, not evidence of correctness.
Contributors MUST review AI-assisted output for requirement fit, correctness, security, and
maintainability, and verify claims with project evidence or tests. Confidential data and secrets
MUST NOT be submitted to AI tools.

## Engineering Constraints

Implementation MUST use the project's established language, frameworks, and tooling unless an
approved requirement justifies a change. Dependencies MUST be kept to the minimum needed and
managed through the project's standard dependency files. Configuration that varies by environment
MUST remain separate from source code, and credentials MUST be supplied through secure
configuration rather than committed files.

## Development Workflow and Quality Gates

Work MUST proceed from specification to design and tasks, then implementation and verification.
Each task MUST be traceable to an acceptance criterion. Before completion, review the change for
scope alignment, tests, security and privacy implications, and relevant documentation. User-facing
or operational behavior changes MUST include appropriate documentation updates. Validation results
and known limitations MUST be stated clearly.

## Governance

This constitution governs project specifications, plans, tasks, implementation, and reviews.
Amendments MUST include a rationale and an impact review; affected specifications, plans, and
quality checks MUST be reconciled with the amended principles. Contributors MUST assess compliance
during planning and before completion, and explain any proposed exception for explicit approval.

Constitution versions follow Semantic Versioning: MAJOR for incompatible changes to principles or
governance, MINOR for new principles or materially expanded requirements, and PATCH for
clarifications that do not change obligations.

**Version**: 1.0.0 | **Ratified**: 2026-11-02 | **Last Amended**: 2026-11-02
