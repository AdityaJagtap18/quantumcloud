# REQUIREMENTS_TRACEABILITY.md — Requirement → Module → API → Test Mapping

## 1. Traceability Matrix

| Requirement | Module | API endpoint(s) | DB entity | Test(s) | Status |
|---|---|---|---|---|---|
| FR-AUTH-001 | A | `POST /auth/register` | `users` | `test_register_new_user`, `test_register_duplicate_email_rejected` | ✅ |
| FR-AUTH-002 | A | `POST /auth/login` | `users` | `test_login_success`, `test_login_wrong_password_rejected` | ✅ |
| FR-AUTH-003 | A | all protected endpoints | — | `test_protected_endpoint_requires_auth`, `test_protected_endpoint_rejects_garbage_token` | ✅ |
| FR-AUTH-004 | A | `GET /jobs/{id}` | `quantum_jobs` | `test_unauthorized_job_access_rejected` | ✅ |
| FR-AUTH-005 | A | *(planned)* `GET /users/me` | `users` | — | ⬜ Release 3 |
| FR-QC-001 | B | `POST /circuits/validate` | — | `test_circuit_validation_rejects_bad_qubit_index`, `test_circuit_validation_rejects_wrong_param_count`, `test_validate_good_circuit`, `test_validate_bad_circuit` | ✅ |
| FR-QC-002 | B, D | `POST /jobs` | `quantum_jobs` | `test_invalid_circuit_rejected` | ✅ |
| FR-QC-003 | B | `POST /jobs`, `/circuits/*` | `quantum_jobs.circuit_config` | (covered by all circuit-accepting tests) | ✅ |
| FR-QC-004 | B | — | — | manual browser verification of gate palette | ✅ (UI); automated coverage is via JSON, not per-gate UI tests |
| FR-QC-005 | B, I | `POST /algorithms/quantum_teleportation/load` | — | teleportation round-trip test in algorithm library test module | ✅ |
| FR-QC-006 | B | — | — | code review of `circuit_builder.py` | ✅ (static review, not a runtime test) |
| FR-QC-007 | B | — | — | manual browser verification | ✅ (manual only) |
| FR-BE-001 | C | `GET /backends` | `quantum_backends` | implicit in every job test (all submit via a real `backend_id`) | ✅ |
| FR-BE-002 | C | `GET /backends` | `quantum_backends` | `test_bell_state_correctness` | ✅ |
| FR-BE-003 | C | `POST /jobs` | — | `test_statevector_backend_rejects_too_many_qubits` | ✅ |
| FR-BE-004 | C | `POST /jobs` (backend_type=noisy) | — | `test_noise_model_changes_distribution` | ✅ |
| FR-BE-005 | C | `POST /jobs` (backend_type=custom_noise) | — | `test_custom_noise_config_requires_measurements_runs` | ✅ |
| FR-BE-006 | C | `GET /backends` | `quantum_backends.configuration` | manual review of description text | ✅ |
| FR-BE-007 | C | — | — | architectural review only | ✅ (design) |
| FR-JOB-001..002 | D | `POST /jobs` | `quantum_jobs` | `test_submit_job_and_retrieve_results` | ✅ |
| FR-JOB-003 | D | `POST /jobs` | — | code review (`queue.py` `is_async` logic) | ✅ (design); not load-tested |
| FR-JOB-004 | D | `GET /jobs/{id}` | `quantum_jobs.status` | `test_job_not_found_returns_404`, integration test | ✅ |
| FR-JOB-005 | D | `GET /jobs/{id}/results` | `quantum_results` | `test_submit_job_and_retrieve_results` | ✅ |
| FR-JOB-006 | D | `POST /jobs/{id}/cancel` | `quantum_jobs.status` | `test_job_cancellation_before_execution` | ✅ |
| FR-JOB-007 | D | — | — | `job_timeout` parameter set; no dedicated test | ⚠️ gap (ROADMAP P1) |
| FR-JOB-008 | D | — | — | not implemented | ⬜ Release 2 follow-up |
| FR-JOB-009 | D | — | `quantum_jobs`, `quantum_results` | implicit in `test_invalid_circuit_rejected` (no orphaned result row) | ✅ |
| FR-ENG-001..005 | E | `POST /jobs`, `/circuits/analyze`, `/circuits/transpile` | — | `test_quantum_engine.py` (13 tests) | ✅ |
| FR-ENG-006 | E | — | — | process followed; version pins in `requirements.txt` | ✅ (process) |
| FR-RES-001..008 | F | `POST /circuits/analyze`, `/circuits/transpile` | — | `test_transpilation_changes_gate_set_for_linear_topology`, `test_logical_vs_transpiled_gate_counts_are_distinguished`, `test_transpile_endpoint_reports_overhead` | ✅ |
| FR-RESULT-001..005, 007 | G | `GET /jobs/{id}/results` | `quantum_results` | `test_submit_job_and_retrieve_results`, manual export verification | ✅ |
| FR-RESULT-006 | G | — | — | not implemented on Job Details page | ⬜ Release 3 |
| FR-RESULT-008 | G | — | — | not implemented | ⬜ Release 3 |
| FR-NOISE-001..005 | H | `POST /experiments`, `GET /experiments/{id}` | `experiments`, `experiment_runs` | integration test's noise-sweep assertions | ✅ |
| FR-NOISE-006 | H | `GET /experiments` | `experiments` | API implemented; no list/detail frontend | ⚠️ partial (API ✅, UI ⬜) |
| FR-ALG-001..003 | I | `GET /algorithms`, `POST /algorithms/{id}/load` | — | `test_list_algorithms_returns_all`, `test_load_bernstein_vazirani_and_run_recovers_secret` | ✅ |

## 2. Consistency Review

As required by the brief, before calling this documentation package
complete:

- **Every major functional requirement maps to an implementation
  module.** ✅ — confirmed by the "Module" column above; no FR-* item
  lacks a module (A–I).
- **Every API maps to one or more requirements.** ✅ — cross-checked
  against `API_SPECIFICATION.md`; every endpoint listed there appears
  in the traceability matrix's "API endpoint(s)" column at least once,
  except `GET /health` (infrastructure, not a product requirement —
  intentionally excluded) and `GET /backends/{id}` /
  `GET /algorithms/{id}` (detail-view variants of their list
  counterparts, covered under the same FR as the list endpoint).
- **Every persistent entity has a clear purpose.** ✅ — see
  `DATABASE_DESIGN.md` §2; every table (`users`, `quantum_backends`,
  `quantum_jobs`, `quantum_results`, `experiments`, `experiment_runs`)
  is referenced by at least one FR-* row above.
- **Every MVP (Release 1) feature has acceptance criteria.** ✅ — see
  PRD.md §12 Release 1's six numbered acceptance criteria, each traced
  to a specific module/test above.
- **Every critical workflow has a testing strategy.** ✅ — Journeys
  1–4 in `USER_FLOWS.md` each map to the automated tests cited in
  their "Verified" notes, plus the gaps explicitly listed in
  `TESTING_STRATEGY.md` §7 rather than silently omitted.
- **Every technical risk has a mitigation plan.** ✅ — see
  `RISK_REGISTER.md`; every row has a non-empty "Mitigation" column,
  including risks whose mitigation is honestly "not yet verified" with
  a reason, rather than a fabricated reassurance.

## 3. Known Inconsistencies Surfaced by This Review

1. **API versioning:** this document and `API_SPECIFICATION.md`
   specify `/api/v1/...`; the actual running code uses unversioned
   `/api/...`. Resolved by explicit flag (not silently glossed over)
   in `API_SPECIFICATION.md`'s implementation note and `ROADMAP.md`'s
   P0 backlog item.
2. **`experiment_runs.job_id` is always null** in the current
   implementation, despite the schema modeling it as an optional link
   to a real job — because noise-sweep points execute synchronously
   inline rather than through the job queue. This is a deliberate
   simplification for Release 2, not a bug, and is called out in
   `DATABASE_DESIGN.md` and `RISK_REGISTER.md`'s "Unresolved Decisions."
3. **User Settings (Screen 9) and its backing endpoint do not exist
   yet**, despite being named in the UI/UX requirements list — resolved
   by marking it "planned" everywhere it's referenced rather than
   describing a screen that isn't there.

This document intentionally keeps "✅ implemented and tested," "✅
design/process only," and "⬜ not yet done" visually distinct
throughout, per the brief's instruction to never claim a capability
that was not actually verified.
