# feature-full-cycle.md

## Purpose
This document instructs the agent to develop **one feature end-to-end**, across:
- Marketing
- Sales
- Product
- Engineering
- QA
- Deployment
- Customer-facing delivery

Reading this document is sufficient to execute the feature **in full**, autonomously.

---

## Core Principle

A feature is not code.

A feature is complete **only when**:
- It is buildable
- It is sellable
- It is discoverable
- It is measurable
- It is delivered to users
- It is reflected in docs, roadmap, PRD, and filesystem

Anything less is **partial work**.

---

## Input Assumptions

Before starting, the agent MUST locate and read:
1. `PRD.yml`
2. `roadmap.yml`
3. Active sprint YAML
4. Current filesystem state
5. `execution-contract.md`
6. `agile-tdd-method.md`

If inconsistencies exist, **resolve them first** and update docs.

---

## Phase 1 — Market & Positioning

### Goals
- Understand **who this feature is for**
- Understand **why it exists**
- Define **how it will be communicated**

### Actions
1. Identify target user persona(s)
2. Identify problem solved in 1 sentence
3. Identify primary value proposition
4. Define feature name (external, user-facing)
5. Define 1–3 key benefit bullets

### Mandatory Outputs
- Marketing headline
- Short description (≤ 3 sentences)
- Primary CTA (e.g. “Start free”, “Book demo”, “Enable feature”)

Outputs must be written to:
- PRD (marketing section)
- Feature directory (README or metadata)

---

## Phase 2 — Sales Enablement

### Goals
- Make the feature sellable
- Reduce friction for sales conversations

### Actions
1. Identify when this feature is pitched:
   - Before sale
   - During sale
   - After sale (upsell / retention)
2. Identify objections it removes
3. Define pricing impact (if any)
4. Define qualification trigger (when to mention it)

### Mandatory Outputs
- Sales pitch paragraph
- Objection → response bullets
- CTA wording for sales

Outputs must be written to:
- PRD (sales section)
- Roadmap notes (if revenue-impacting)

---

## Phase 3 — Product Definition

### Goals
- Translate business intent into exact behavior

### Actions
1. Define feature scope (in / out)
2. Define user flows
3. Define acceptance criteria
4. Define edge cases
5. Define success metrics

### Mandatory Outputs
- Updated PRD with:
  - Functional requirements
  - Non-functional requirements
  - Acceptance criteria
  - Metrics

No engineering work may begin without this.

---

## Phase 4 — Engineering Execution (TDD)

### Goals
- Build the feature correctly and safely

### Actions
1. Create feature branches:
   - `feature-name/dev`
   - `feature-name/test`
2. Tester:
   - Writes black-box tests validating PRD
   - Uses public APIs only
3. Developer:
   - Implements feature
   - Writes unit tests
4. Integrate into `feature-name` branch
5. Merge to `main`

All execution follows `agile-tdd-method.md`.

---

## Phase 5 — Deployment & Validation

### Goals
- Ensure the feature works in production

### Actions
1. Deploy to target environment
2. Execute post-deploy validation
3. Verify metrics are emitted
4. Verify feature flag / exposure logic

### Mandatory Outputs
- Deployment confirmation
- Validation results
- Fixes if required

---

## Phase 6 — Go-To-Market Activation

### Goals
- Ensure users can discover and use the feature

### Actions
1. Create release note entry
2. Update user-facing docs
3. Ensure CTA is reachable in product
4. Ensure marketing copy matches behavior

### Mandatory Outputs
- Release notes
- Docs updated
- CTA visible and functional

---

## Phase 7 — Sprint Closure & State Update

### Goals
- Make the work **officially complete**

### Actions
1. Update sprint YAML:
   - Mark story complete
   - Mark sprint complete if applicable
2. Update:
   - PRD
   - Roadmap
   - Filesystem truth
3. Commit all updates to `main`

If not committed, it is not done.

---

## Phase 8 — Feedback Loop

### Goals
- Prepare for iteration

### Actions
1. Capture:
   - Client feedback
   - Usage signals
   - Issues or gaps
2. Record new inputs as:
   - Feature
   - Bug
   - Minor improvement
3. Update roadmap and PRD accordingly

---

## Auto-Mode Rules

When auto-mode is enabled:
- Do not ask questions
- Resolve ambiguity pragmatically
- Prefer shipping over waiting
- Log decisions via commits and docs

Difficulty is qualitative only:
- easy / medium / hard

---

## Final Definition of Done

A feature is DONE only when:
- It exists in production
- It is test-covered
- It is documented
- It has a CTA
- It is sellable
- It is reflected in sprint YAML, PRD, roadmap, and git

Anything else is unfinished work.
