# full-qa-cycle.md

## Purpose
This document instructs the agent to execute a **complete, end-to-end QA cycle** for the application.
The cycle covers **automated testing, integration testing, production-like validation, and agent-driven exploratory QA**, and ensures all findings are **recorded, classified, and fed back** into the system of record.

Reading this document is sufficient to perform QA autonomously.

---

## Scope
This QA cycle applies to:
- Backend services
- Frontend applications (web / mobile)
- APIs
- Integrations
- Deployed environments

QA is not complete until **all layers** have been validated.

---

## Preconditions

Before starting QA, the agent MUST:
1. Identify the target environment:
   - local
   - staging
   - production
2. Read:
   - `PRD.yml`
   - `roadmap.yml`
   - Active sprint YAML
   - `execution-contract.md`
3. Ensure the filesystem reflects the latest code on `main`.

If preconditions are not met, **fix them first**.

---

## Phase 1 — Automated Test Execution

### Backend
1. Install dependencies
2. Run:
   - Unit tests
   - Integration tests
   - API contract tests
3. Capture:
   - Failures
   - Warnings
   - Flaky tests
   - Coverage gaps

### Frontend
1. Run:
   - Unit tests
   - Component tests
   - E2E tests (if present)
2. Validate:
   - Build succeeds
   - Linting passes
   - Static analysis results

### Mandatory Outputs
- Test results summary
- List of failures and gaps

---

## Phase 2 — Environment Validation (Real Server)

1. Deploy or connect to target environment
2. Verify:
   - Services are healthy
   - APIs respond correctly
   - Frontend loads without errors
3. Validate configuration:
   - Environment variables
   - Feature flags
   - External integrations

Any blocking issue must be fixed before continuing.

---

## Phase 3 — Black-Box QA

### Goals
Validate the system strictly from the **user-facing perspective**, ignoring internal implementation.

### Actions
1. Use only:
   - Public APIs
   - Public UI
2. Execute:
   - Core user flows
   - Edge cases
   - Error scenarios
3. Validate against PRD acceptance criteria

### Mandatory Outputs
- Black-box pass/fail per acceptance criterion
- Missing or ambiguous requirements

---

## Phase 4 — Exploratory (“Manual by Agent”) QA

### Goals
Simulate a human user exploring the product.

### Actions
1. Navigate through the app:
   - Click all accessible buttons
   - Fill all forms
   - Trigger all visible actions
2. Test:
   - Happy paths
   - Invalid inputs
   - Unexpected sequences
3. Observe:
   - UX friction
   - Missing feedback
   - Confusing flows
   - Inconsistent behavior
4. Take structured notes during exploration

This phase is **intentionally non-scripted**.

---

## Phase 5 — Issue Classification & Recording

Each finding MUST be classified as exactly one of:

- **Bug**
- **Missing feature**
- **UX / usability issue**
- **Performance issue**
- **Improvement / enhancement**

### Storage Rules
Findings MUST be saved as structured files in:

- `.seedgpt/bugs/`
- `.seedgpt/features/`
- `.seedgpt/minor-improvements/`

Each item must include:
- Title
- Description
- Reproduction steps
- Expected vs actual behavior
- Severity (low / medium / high / critical)
- Affected area (backend / frontend / API)

---

## Phase 6 — Plan & Document Updates

After recording findings, the agent MUST:

1. Update `roadmap.yml`:
   - Add new items
   - Reprioritize if required
2. Update `PRD.yml`:
   - Clarify ambiguous requirements
   - Add missing acceptance criteria
3. Update sprint YAML:
   - Add follow-up work to future sprint
4. Ensure filesystem reflects new reality

All updates must be committed to `main`.

---

## Phase 7 — QA Summary & Exit

### Mandatory Outputs
- QA summary (pass/fail status)
- List of blocking vs non-blocking issues
- Recommendation:
  - ready to release
  - release with known issues
  - not ready

### Final Rule
QA is considered **complete** only when:
- All tests executed
- All findings recorded and classified
- All plans and docs updated
- State committed to git

---

## Auto-Mode Rules

When auto-mode is enabled:
- Do not ask questions
- Continue despite non-critical issues
- Log all decisions via structured files and commits

---

## Definition of QA Done

QA is DONE when:
- The system has been tested as code, as APIs, and as a user
- All defects and gaps are captured
- No knowledge remains in the agent’s head only

If it is not written down, it does not exist.
