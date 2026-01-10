# execution-contract.md

## Purpose
This document defines the **single binding execution contract** for the company.
It governs **when work may start, how it is executed, and when it is considered complete**.
It applies to **all work types**: features, bugs, minor improvements, refactors.

This contract is **authoritative** over all other process documents.

---

## Scope
This contract applies to:
- Sales-driven work
- Roadmap items
- Engineering execution
- Testing and validation
- Deployment
- Documentation
- Client-facing delivery

If an activity is not compliant with this contract, it is **invalid work**.

---

## Entry Criteria (When Work May Start)

Work on any task MAY START **only if all conditions are true**:

1. A valid item exists in exactly one of:
   - `.seedgpt/features/`
   - `.seedgpt/bugs/`
   - `.seedgpt/minor-improvements/`

2. The item is referenced in:
   - `roadmap.yml` with `status: active` or `status: planned`
   - `PRD.yml` with clear scope and acceptance criteria

3. A sprint entry exists in:
   - `.seedgpt/sprints/sprint-vXX-*.yml`
   - The item is assigned to that sprint

4. The filesystem represents the **current truth** of the project.

If any of the above is missing or outdated → **work must not start**.

---

## Execution Rules (How Work Is Performed)

1. Execution MUST follow `agile-tdd-method.md` exactly.
2. Development and testing are treated as **separate responsibilities**.
3. Tests validate the PRD as a **black box** using official APIs.
4. All work is performed on feature-scoped branches.
5. CI must be green at every merge boundary.

Parallel execution is allowed and preferred.

---

## Mandatory Artifacts (What Must Be Produced)

For each completed task, the following artifacts MUST exist:

### Code & Tests
- Production code
- Unit tests
- Black-box / integration tests
- Clear filesystem hierarchy and naming

### Git
- Feature branch
- Merged into `main`
- Clean, traceable commit history

### Sprint State
- Sprint YAML updated:
  - Story marked `status: complete`
  - `completed_date` set
- If sprint finished:
  - Sprint marked `status: complete`
  - `progress: 100`

### Documentation
- `PRD.yml` updated to reflect reality
- `roadmap.yml` updated with current status
- Filesystem reflects actual state, not intent

If **any artifact is missing**, the task is **not complete**.

---

## Exit Criteria (When Work Is Done)

Work is considered **DONE** only when ALL conditions are met:

1. Code merged to `main`
2. All tests pass (local + CI)
3. Sprint YAML updated and committed
4. PRD and roadmap updated
5. Deployment completed (if applicable)
6. Post-deployment validation executed
7. Current project state is fully reflected in git

Green CI alone is **not sufficient**.

---

## Auto-Mode & Autonomy Rules

When auto-mode is enabled:
- No user questions are asked
- All decisions are made autonomously
- Ambiguity is resolved pragmatically
- Decisions are logged via commits and docs

Time estimation is qualitative only:
- easy / medium / hard

Human-hours accounting is explicitly ignored.

---

## Enforcement

This contract is **self-enforcing** via:
- Git history
- Sprint YAML state
- Filesystem truth

Violations must be corrected immediately.
There is no concept of “almost done”.

---

## Final Rule

If it is not:
- in git
- tested
- documented
- reflected in sprint YAML

**It does not exist.**
