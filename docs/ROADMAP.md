# ROADMAP.md — Phased Implementation Roadmap

This roadmap restates PRD §12's three releases as an implementation
sequence, and adds a prioritized backlog of what is *not yet* done
(either never started, or a named gap surfaced in `TESTING_STRATEGY.md`
and `RISK_REGISTER.md`), ordered by priority.

## Release 1 — Core QCaaS MVP
**Status: ✅ Implemented and tested (except live Docker verification)**

Scope, deliverables, acceptance criteria: see PRD.md §12.

## Release 2 — Quantum Engineering Capabilities
**Status: ✅ Implemented and tested**

Scope, deliverables, acceptance criteria: see PRD.md §12.

**Follow-up items surfaced during Release 2 (not yet done):**
- Add `/api/v1` path versioning to all routers (currently unversioned
  `/api/...` — see `API_SPECIFICATION.md` note).
- Configure RQ retry policy for transient worker failures (FR-JOB-008).
- Add an automated test for the execution-timeout → FAILED transition.

## Release 3 — Advanced Platform
**Status: ✅ Implemented and tested for items 1–2; item 3 verified by
architectural review only** (see PRD.md §12).

**Follow-up items surfaced during Release 3 (not yet done):**
- User Settings screen (FR-AUTH-005, `GET /api/v1/users/me`).
- Circuit diagram display on the Job Details page (FR-RESULT-006) —
  currently only shown in the Circuit Lab editor itself.
- Cross-job historical comparison view (FR-RESULT-008).
- Experiment list/detail UI in the Noise Studio (API exists; frontend
  currently only shows the most recently run sweep, not a browsable
  history — FR-NOISE-006 gap).
- Teleportation fidelity made directly observable via an optional
  basis-rotation step before final measurement (PRD §4 Module I note).
- A dedicated Backend Selection/comparison screen distinct from the
  inline selector in Circuit Lab (PRD §11 note on Screen 3).

## Prioritized Backlog (beyond the three releases)

| Priority | Item | Why it's next | Depends on |
|---|---|---|---|
| P0 | Live-verify Docker Compose stack against real Postgres + Redis | Closes the single largest unverified claim in this whole document set | Docker availability |
| P0 | Add `/api/v1` prefix | Mechanical, low-risk, closes a documented spec/implementation gap | None |
| P1 | RQ retry policy for transient failures (FR-JOB-008) | Reliability gap identified in NFR §6.3 | None |
| P1 | Execution-timeout automated test | Currently an unverified configuration, not an unverified behavior, but still untested | None |
| P1 | Browser-level E2E suite (Playwright/Cypress) covering Journeys 1–4 | Manual verification doesn't catch regressions automatically | CI infra decision |
| P2 | User Settings screen + `/users/me` endpoint | Small, isolated, low risk | None |
| P2 | Experiment history list/detail UI | API already supports it; pure frontend work | None |
| P2 | Load/concurrency benchmark to replace the "not yet measured" entries in PRD §6.1 | Needed before any real multi-user deployment | Realistic worker hardware sizing |
| P3 | Physical hardware backend (e.g., IBM Quantum provider) | Explicitly out of scope per brief; architecture is ready (FR-BE-007) | Hardware access/credentials, which this project does not have |
| P3 | Centralized logging/metrics (observability, NFR §6.6) | Appropriate once this moves beyond a single-team prototype | Deployment target decision |

## Sequencing Rationale

Release boundaries follow dependency order, not just priority: Release
2's noise/transpilation/resource-analysis features all build on
Release 1's job/backend model existing first (a noise sweep is "run
several jobs with different noise configs," which presupposes a
working job pipeline). Release 3's algorithm library and visual editor
are UX layers on top of the same circuit JSON contract Release 1
already defined — they did not require changing that contract, which
is itself evidence the Release 1 data model was designed with the
right extensibility (confirmed in hindsight, not assumed in advance).
