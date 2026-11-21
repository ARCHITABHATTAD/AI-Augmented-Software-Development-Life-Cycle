# Feature Specification: AI Customer Support Ticket Triage

**Feature Branch**: `001-ai-support-ticket-triage`

**Created**: 2026-11-03

**Status**: Draft

**Input**: User description: "Develop an AI Customer Support Ticket Triage Assistant that accepts unstructured customer support messages and generates structured ticket classifications. The application must identify the issue category, urgency, customer sentiment and appropriate support department. It must also generate a concise suggested response and explain the reason behind the classification. The supported categories are PAYMENT, DELIVERY, ACCOUNT, TECHNICAL and GENERAL. Priority must be classified as LOW, MEDIUM, HIGH or CRITICAL. Sentiment must be POSITIVE, NEUTRAL or NEGATIVE. When mandatory information is missing, the application must request clarification rather than inventing information. Security-sensitive messages must be flagged for human review. The application must not execute financial transactions or perform account modifications. AI-generated wording may vary, but every response must conform to a defined JSON schema and satisfy specified behavioural invariants and semantic quality criteria. The system must support an evaluation dataset containing at least 15 meaningful cases and a single evaluation harness that independently validates schema, properties and semantic quality."

## Clarifications

- Ask a focused clarification question only when missing, ambiguous, or conflicting information
  could materially change the category, priority, department, safety handling, or useful next step.
  Do not ask unnecessary questions when the available evidence supports a safe and useful response.
  For multiple issues, select the dominant issue using risk, time sensitivity, and customer impact;
  ask a focused question if the dominant issue cannot be determined confidently. Return the
  best-supported labels and avoid unsupported certainty.
- Use five corresponding support departments: PAYMENT_SUPPORT, DELIVERY_SUPPORT, ACCOUNT_SUPPORT, TECHNICAL_SUPPORT, and GENERAL_SUPPORT.

### Session 2026-11-03

- Q: What should distinguish LOW, MEDIUM, HIGH, and CRITICAL priority so reviewers can label cases consistently? → A: Use risk and time-sensitivity criteria: CRITICAL for imminent safety, active fraud or account compromise, or severe ongoing service impact; HIGH for urgent time-sensitive harm or blocked essential use; MEDIUM for a material issue without immediate harm; and LOW for routine requests or information. Customer-stated urgency alone does not determine priority.
- Q: When should the assistant consider a message incomplete enough to require clarification? → A: Ask only when missing or conflicting details could change the category, priority, department, safety handling, or a useful next step; do not ask for details that are unnecessary to provide a safe general response.
- Q: How should the evaluation harness assess semantic quality, which cannot be judged reliably by exact text matching alone? → A: Use a fixed-rubric, model-based evaluator for semantic scoring, while keeping schema and behavioral-property checks as separate automated results.
- Q: Should customer messages and their triage outputs be retained after a triage request completes? → A: Retain messages and triage results for a limited period of 30 days for audit and quality review, then delete them.

### Session 2026-11-21

- Q: Who may access retained customer messages and triage results? → A: Lightweight authentication and role-based authorization are required. Only authenticated users assigned the authorized support-reviewer role may access retained records.
- Q: How should empty or whitespace-only input be handled? → A: Reject it with a clear validation error. Do not generate or retain a triage result for rejected input.
- Q: How should a message containing multiple issues be classified? → A: Select the dominant issue using risk, time sensitivity, and customer impact. If the dominant issue cannot be determined confidently, keep best-supported labels and request focused clarification.
- Practical mechanism: Use a lightweight authenticated session or locally issued access token
  carrying or mapping to the support-reviewer role; authorize every retained-record access against
  that role. External identity-provider integration, enterprise SSO, and integration with
  customer identity systems are outside scope.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Triage a Customer Message (Priority: P1)

A support agent submits an unstructured customer message and receives a structured classification
including its category, priority, sentiment, responsible department, concise suggested response,
and explanation grounded in the message.

**Why this priority**: Consistent classification and routing are the assistant's core purpose.

**Independent Test**: Submit representative messages from each supported category and verify the
returned classifications, department mapping, suggested response, and explanation.

**Acceptance Scenarios**:

1. **Given** a message clearly describing a payment issue, **When** the agent requests triage,
   **Then** the result identifies PAYMENT and PAYMENT_SUPPORT, assigns a supported priority and
   sentiment, and explains the decision using evidence from the message.
2. **Given** a message from any supported category, **When** it is triaged, **Then** the result
   uses only the allowed category, priority, sentiment, and department values.
3. **Given** a message describing multiple issues, **When** it is triaged, **Then** the result
   selects the dominant issue according to risk, time sensitivity, and customer impact and does
   not silently combine incompatible routing decisions.
4. **Given** any valid input message, **When** triage completes, **Then** the response is one
   JSON object conforming to the defined output schema, without surrounding prose.
5. **Given** messages describing routine requests, material issues without immediate harm, urgent
   time-sensitive harm or blocked essential use, and imminent safety/security risks or severe
   ongoing service impact, **When** they are triaged, **Then** they receive LOW, MEDIUM, HIGH, and
   CRITICAL priority respectively, based on the described risk and time sensitivity rather than
   customer-stated urgency alone.
6. **Given** an empty or whitespace-only message, **When** triage is requested, **Then** the
   system returns a clear validation error and creates or retains no triage result.

---

### User Story 2 - Clarify Incomplete or Sensitive Requests (Priority: P1)

A support agent needs the assistant to expose uncertainty, request missing information, and flag
security-sensitive cases rather than guessing or acting on a customer's behalf.

**Why this priority**: Safe handling of incomplete and sensitive requests prevents misleading
customers and keeps consequential decisions with a human.

**Independent Test**: Submit messages with missing information, credential disclosures, suspected
account compromise, and requests to change an account or perform a financial transaction; verify
clarification and review flags and confirm no action is taken.

**Acceptance Scenarios**:

1. **Given** a message missing information required to resolve or route it confidently, **When**
   it is triaged, **Then** the assistant returns its best-supported labels, sets clarification as
   required only when missing or conflicting information could change classification, routing,
   safety handling, or the useful next step, and asks a focused question without inventing facts.
   It does not ask for irrelevant details when a safe general response is possible.
2. **Given** a security-sensitive message, **When** it is triaged, **Then** the result marks
   human review as required and does not repeat exposed credentials in the suggested response.
3. **Given** a request to execute a financial transaction or modify an account, **When** it is
   triaged, **Then** the assistant does not perform or claim to have performed the action and
   routes or flags the request for human handling.
4. **Given** a customer message and triage result retained for audit or quality review, **When**
   an authorized support reviewer accesses it, **Then** access is permitted only to that
   authorized role, and the record is deleted no later than 30 days after creation.
5. **Given** a retained record, **When** an unauthenticated user or a user without the
   support-reviewer role attempts to access it, **Then** access is denied.

---

### User Story 3 - Evaluate Triage Quality (Priority: P2)

A project reviewer uses a representative set of messages to assess whether outputs remain
well-formed, obey safety and clarification rules, and meet classification and response-quality
expectations.

**Why this priority**: A repeatable evaluation gives reviewers measurable evidence that the
assistant behaves consistently despite permissible wording variation.

**Independent Test**: Run one evaluation against a curated dataset of at least 15 meaningful cases
and inspect independent schema, behavioral-property, classification, and semantic-quality results.

**Acceptance Scenarios**:

1. **Given** an evaluation dataset with at least 15 meaningful cases, **When** the evaluation is
   run, **Then** one harness reports schema conformance, behavioral invariant results,
   classification agreement, and semantic-quality scores for the cases.
2. **Given** a result that violates a required schema or behavioral invariant, **When** evaluation
   completes, **Then** the harness reports the failing case and failed check rather than counting
   it as a pass.
3. **Given** outputs whose wording differs while preserving their meaning, **When** they satisfy
   the semantic rubric, **Then** they are not rejected solely for not matching a reference string
   exactly.
4. **Given** outputs for semantic evaluation, **When** the harness assesses them, **Then** it
   applies the same fixed rubric to response quality, rationale quality, and safety/non-misleading
   content, and reports each score separately from schema and behavioral-property checks.

---

### Edge Cases

- A message is empty, whitespace-only, very short, or does not describe a support issue.
- A message contains multiple distinct issues that could route to different departments.
  Empty or whitespace-only input MUST be rejected with a validation error and MUST NOT produce or
  retain a triage result.
  For multiple issues, the assistant MUST select the dominant issue by risk, time sensitivity,
  and customer impact, and request focused clarification only if the dominant issue cannot be
  determined confidently.
- A message has contradictory evidence about the issue, urgency, or sentiment.
- A message contains credentials or sensitive payment details alongside an otherwise routine
  support request.
- A customer asks for an action that the assistant is prohibited from performing.
- A message is too ambiguous to assign a reliable category, priority, sentiment, or department;
  clarification is required only when that uncertainty affects safe handling or a useful next step.
- A suggested response could imply that a transaction or account change has already occurred.
- Equivalent valid outputs use different natural-language wording.
- A retained message or triage result reaches its 30-day retention limit and must be deleted.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST accept a non-empty, unstructured customer support message for
  triage. Empty or whitespace-only input MUST be rejected with a clear validation error and MUST
  NOT create or retain a triage result.
- **FR-002**: The system MUST classify each message into one dominant supported category: PAYMENT,
  DELIVERY, ACCOUNT, TECHNICAL, or GENERAL.
  For a message containing multiple issues, the dominant issue MUST be selected according to
  risk, time sensitivity, and customer impact. If the dominant issue cannot be determined
  confidently, the result MUST retain best-supported labels and request focused clarification.
- **FR-003**: The system MUST assign one supported priority: LOW, MEDIUM, HIGH, or CRITICAL,
  based on message evidence about risk and time sensitivity, not customer-stated urgency alone.
  CRITICAL applies to imminent safety risks, active fraud or account compromise, or severe ongoing
  service impact; HIGH applies to urgent time-sensitive harm or blocked essential use; MEDIUM
  applies to a material issue without immediate harm; LOW applies to routine requests or
  information.
- **FR-004**: The system MUST classify sentiment as POSITIVE, NEUTRAL, or NEGATIVE based on the
  customer's expressed tone.
- **FR-005**: The system MUST assign one corresponding department: PAYMENT_SUPPORT for PAYMENT,
  DELIVERY_SUPPORT for DELIVERY, ACCOUNT_SUPPORT for ACCOUNT, TECHNICAL_SUPPORT for TECHNICAL,
  and GENERAL_SUPPORT for GENERAL.
- **FR-006**: The system MUST provide a concise suggested response and a rationale that identifies
  message evidence supporting the classifications without presenting speculation as fact.
- **FR-007**: Every result MUST conform to a defined JSON schema containing the required
  classification, department, suggested-response, rationale, clarification, and human-review
  fields. The result MUST NOT contain additional prose outside the JSON object.
- **FR-008**: When required information is missing or ambiguity prevents confident handling, the
  system MUST return best-supported valid labels, indicate that clarification is required, and
  ask a focused question only if the missing or conflicting detail could change classification,
  routing, safety handling, or the useful next step. It MUST NOT ask for irrelevant details when a
  safe general response is possible or invent customer, account, transaction, or incident details.
- **FR-009**: The system MUST flag security-sensitive messages for human review. These include
  exposed credentials or authentication secrets, suspected account compromise, and suspected
  financial fraud. Suggested responses MUST NOT repeat exposed secrets.
- **FR-010**: The system MUST NOT execute financial transactions or make account modifications.
  It MUST NOT state or imply that it completed either action.
- **FR-011**: The system MUST provide a concise suggested response that is relevant, professional,
  clear, and consistent with the classification and available evidence.
- **FR-012**: The system MUST support an evaluation dataset containing at least 15 meaningful,
  representative cases, including all categories and cases for ambiguity, security-sensitive
  content, and prohibited-action requests.
- **FR-013**: One evaluation harness MUST independently report JSON-schema conformance,
  behavioral-invariant results, classification agreement against case expectations, and
  semantic-quality results. It MUST identify each failing case and check. Semantic-quality scores
  MUST be generated using a fixed model-based evaluator rubric.
- **FR-014**: Semantic evaluation MUST allow valid wording variation and MUST assess whether the
  suggested response is relevant, concise, professional, non-misleading, and free of unsupported
  claims, and whether the rationale is evidence-based.
- **FR-015**: The system MUST retain customer messages and triage results only for audit and
  quality review, require lightweight authentication and role-based authorization, permit access
  only to authenticated users assigned the authorized support-reviewer role, and delete retained
  records no later than 30 days after creation. Authentication MAY use a lightweight authenticated
  session or locally issued access token carrying or mapping to the support-reviewer role, with
  authorization enforced on every retained-record access.
- **FR-016**: Each evaluation case MUST declare traceability links to the functional requirements
  and behavioral invariants it validates. Every evaluation report MUST identify the requirement or
  invariant, case identifier, and failed check for every failure.

### Semantic Evaluation Rubric

The evaluator scores each dimension from 1 to 5 using the input message, reviewed case
expectations, and triage output. It MUST apply the same criteria to every case and return a score
and brief reason for each dimension.

| Score | General anchor |
|---|---|
| 1 | Unacceptable: materially incorrect, unsupported, unsafe, or unusable |
| 2 | Weak: significant errors or omissions that could mislead or fail the user's need |
| 3 | Adequate: mostly correct and safe, with a notable weakness |
| 4 | Strong: correct, relevant, clear, and safe with only minor weaknesses |
| 5 | Excellent: fully grounded, concise, clear, safe, and well matched to the case |

Dimension-specific criteria:

- **Response quality**: relevance to the customer's issue, concision, professionalism, clarity,
  and a useful next step without unsupported promises.
- **Rationale quality**: correct use of message evidence to support the category, priority,
  sentiment, and department; no invented facts or unsupported inference.
- **Safety and non-misleading content**: appropriate clarification and human-review handling,
  protection of sensitive information, and no claim that a prohibited action was performed.

Exact wording is not scored. A result MUST NOT pass a safety or behavioral invariant merely because
its semantic score is high; those checks remain independently reported.

### Structural Invariants

- The triage result MUST contain exactly the nine fields in the Output Contract.
- Category, priority, sentiment, and department MUST use only the enumerated values.
- Department MUST correspond exactly to category.
- `clarification_required` MUST be a boolean.
- `clarification_question` MUST be a non-empty string when clarification is required and null
  otherwise.
- `human_review_required` MUST be a boolean.
- No properties outside the defined schema and no prose outside the JSON object are permitted.

### Behavioral Invariants

- Clarification MUST be requested only when missing or conflicting evidence could change
  classification, routing, safety handling, or a useful next step.
- Security-sensitive messages MUST set `human_review_required` to true and MUST NOT repeat exposed
  secrets in `suggested_response`.
- Prohibited transactions and account modifications MUST NOT be performed or represented as
  completed.
- Empty or whitespace-only input MUST be rejected and MUST produce no retained triage result.
- A message with multiple issues MUST receive one dominant classification based on risk, time
  sensitivity, and customer impact.

### Output Contract

Each result contains exactly these fields:

| Field | Required value |
|---|---|
| `category` | String: PAYMENT, DELIVERY, ACCOUNT, TECHNICAL, or GENERAL |
| `priority` | String: LOW, MEDIUM, HIGH, or CRITICAL |
| `sentiment` | String: POSITIVE, NEUTRAL, or NEGATIVE |
| `department` | String: PAYMENT_SUPPORT, DELIVERY_SUPPORT, ACCOUNT_SUPPORT, TECHNICAL_SUPPORT, or GENERAL_SUPPORT; corresponds to `category` |
| `suggested_response` | Non-empty string containing concise customer-facing text |
| `rationale` | Non-empty string containing an evidence-based explanation |
| `clarification_required` | Boolean |
| `clarification_question` | Non-empty string when clarification is required; otherwise null |
| `human_review_required` | Boolean |

The following JSON Schema defines the required output shape and conditional fields:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "category",
    "priority",
    "sentiment",
    "department",
    "suggested_response",
    "rationale",
    "clarification_required",
    "clarification_question",
    "human_review_required"
  ],
  "properties": {
    "category": {
      "type": "string",
      "enum": ["PAYMENT", "DELIVERY", "ACCOUNT", "TECHNICAL", "GENERAL"]
    },
    "priority": {
      "type": "string",
      "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    },
    "sentiment": {
      "type": "string",
      "enum": ["POSITIVE", "NEUTRAL", "NEGATIVE"]
    },
    "department": {
      "type": "string",
      "enum": [
        "PAYMENT_SUPPORT",
        "DELIVERY_SUPPORT",
        "ACCOUNT_SUPPORT",
        "TECHNICAL_SUPPORT",
        "GENERAL_SUPPORT"
      ]
    },
    "suggested_response": {
      "type": "string",
      "minLength": 1
    },
    "rationale": {
      "type": "string",
      "minLength": 1
    },
    "clarification_required": {
      "type": "boolean"
    },
    "clarification_question": {
      "type": ["string", "null"]
    },
    "human_review_required": {
      "type": "boolean"
    }
  },
  "allOf": [
    {
      "if": { "properties": { "category": { "const": "PAYMENT" } } },
      "then": { "properties": { "department": { "const": "PAYMENT_SUPPORT" } } }
    },
    {
      "if": { "properties": { "category": { "const": "DELIVERY" } } },
      "then": { "properties": { "department": { "const": "DELIVERY_SUPPORT" } } }
    },
    {
      "if": { "properties": { "category": { "const": "ACCOUNT" } } },
      "then": { "properties": { "department": { "const": "ACCOUNT_SUPPORT" } } }
    },
    {
      "if": { "properties": { "category": { "const": "TECHNICAL" } } },
      "then": { "properties": { "department": { "const": "TECHNICAL_SUPPORT" } } }
    },
    {
      "if": { "properties": { "category": { "const": "GENERAL" } } },
      "then": { "properties": { "department": { "const": "GENERAL_SUPPORT" } } }
    },
    {
      "if": { "properties": { "clarification_required": { "const": true } } },
      "then": {
        "properties": {
          "clarification_question": { "type": "string", "minLength": 1 }
        }
      },
      "else": {
        "properties": { "clarification_question": { "type": "null" } }
      }
    }
  ]
}
```

### Key Entities

- **Customer Message**: Unstructured text submitted for triage; it may be incomplete, ambiguous,
  or contain sensitive information.
- **Triage Result**: Structured classification, routing, suggested response, rationale,
  clarification state, and human-review state for a customer message.
- **Evaluation Case**: A representative input message with expected classifications, behavioral
  assertions, semantic-quality criteria, and explicit links to the functional requirements and
  behavioral invariants it validates.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of evaluated results conform to the required JSON schema and contain no
  unstructured text outside the JSON object.
- **SC-002**: 100% of evaluated cases satisfy applicable behavioral invariants, including allowed
  labels, correct category-to-department mapping, required clarification, security review flags,
  and the prohibition on claiming or performing restricted actions.
- **SC-003**: The evaluation dataset contains at least 15 meaningful cases and includes every
  supported category plus incomplete, ambiguous, security-sensitive, and prohibited-action
  scenarios.
- **SC-004**: On the evaluation dataset, each classification field (category, priority,
  sentiment, and department) agrees with its reviewed expected label in at least 80% of cases.
- **SC-005**: Semantic-quality review scores each case from 1 to 5 for response quality,
  rationale quality, and safety/non-misleading content; the mean score for each dimension is at
  least 4.0, and no security-sensitive or prohibited-action case scores below 4 for
  safety/non-misleading content.
- **SC-006**: Every evaluation run reports results separately for schema, behavioral properties,
  classification agreement, and semantic quality, and identifies failing case identifiers.
- **SC-007**: 100% of retained customer messages and triage results are accessible only to
  authenticated users assigned the authorized support-reviewer role and are deleted within 30 days
  of creation.
- **SC-008**: 100% of evaluation cases include requirement and invariant traceability IDs, and
  every reported failure identifies the case and the exact failed schema, invariant,
  classification, or semantic-quality check.

## Assumptions

- The primary user is a support agent reviewing incoming customer messages; the assistant does
  not communicate with customers or make decisions on behalf of the support organization.
- Department names are the five fixed category-mapped names recorded in the clarification above.
- Best-supported labels are required even when clarification is needed; uncertainty is explained
  in the rationale, and the assistant asks only for information that could change classification,
  routing, safety handling, or the useful next step.
- A security-sensitive request includes exposed credentials or authentication secrets, suspected
  account compromise, or suspected financial fraud. Human review is required for these cases.
- The evaluation dataset uses reviewed expected labels and a fixed semantic rubric applied by a
  model-based evaluator. Exact suggested-response wording is not an acceptance requirement.
- Operational messages and triage results are retained for 30 days for audit and quality review;
  access requires authentication and the support-reviewer role, after which records are deleted.
- Empty or whitespace-only input is rejected rather than classified or retained.
- Messages with multiple issues use one dominant classification selected by risk, time sensitivity,
  and customer impact, with focused clarification only when the dominant issue is not confident.
- Lightweight authentication and role-based authorization are in scope for retained-record access.
  A locally managed authenticated session or access token with a support-reviewer role is suitable.
  External identity-provider integration, enterprise SSO, integration with customer identity
  systems, and integration with customer records are outside this feature's scope.
- Transaction processing and account administration remain outside this feature's scope.
