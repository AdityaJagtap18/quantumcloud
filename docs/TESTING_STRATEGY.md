# TESTING_STRATEGY.md — QuantumCloud Test Plan

## 1. Testing Levels

| Level | Tool | Location | What it covers |
|---|---|---|---|
| Unit | pytest | `backend/tests/test_quantum_engine.py` | Gate construction, kernel/circuit correctness, validation rules, resource analysis |
| API | pytest + FastAPI `TestClient` | `test_auth_api.py`, `test_jobs_api.py`, `test_circuits_and_algorithms_api.py` | Per-endpoint contract: status codes, auth/ownership enforcement, error shapes |
| Integration | pytest + `TestClient` | `test_integration.py` | Full register→load→analyze→submit→poll→retrieve→noise-sweep path, no mocked quantum execution |
| Manual/E2E | Browser automation (this project's development process) | N/A (not scripted into CI) | Visual correctness, real end-user workflows — see §5 |

**Why no mocking of quantum execution anywhere:** the entire point of
this product is that results are real. A test suite that mocks
`execute_circuit` would pass even if Qiskit Aer were silently broken —
exactly the failure mode this strategy exists to catch (and did catch,
twice, during development: the `qiskit.execute()` removal and the
`c_if` removal, both surfaced by tests failing for real reasons).

## 2. Test Environment

`REDIS_URL=fakeredis://` makes the job queue synchronous
(`is_async=False`), so `POST /api/v1/jobs` has already executed the
job via the *real* `execute_circuit` function by the time the HTTP
response is returned — no sleep/poll loop is needed in tests, and no
execution path is skipped. `DATABASE_URL=sqlite:///...` substitutes for
Postgres; schema compatibility is not a concern here because the ORM
models and the generated Alembic migration are database-agnostic (no
Postgres-specific column types are used).

## 3. Deterministic vs. Statistical Acceptance Tests

This distinction is load-bearing and explicit throughout the suite:

- **Deterministic tests** assert an *exact* value and require no
  tolerance: statevector norm == 1.0 (±1e-9 float tolerance only),
  Bernstein-Vazirani's secret recovered with probability 1
  (`{"101": 1000}` for 1000 shots, no other bitstring), measurement
  counts summing exactly to the requested shot count, kernel-matrix
  symmetry.
- **Statistical tests** assert a *range*, with the tolerance stated as
  a number, not "should be close": Bell state counts for `00`/`11`
  each between 40–60% of 4000 shots (a generous band chosen to make
  the test non-flaky while still catching a genuinely broken circuit,
  which would produce a result far outside that band — e.g., all
  probability on one outcome, or a 25/25/25/25 split across all four
  2-qubit outcomes).

### Bell state acceptance test (reference)
```python
result = execute_circuit(bell_circuit, "ideal_qasm", shots=4000)
counts = result.measurement_counts
assert set(counts.keys()) <= {"00", "11"}      # deterministic: no other outcome possible
assert sum(counts.values()) == 4000             # deterministic
assert 0.4 < counts.get("00", 0) / 4000 < 0.6    # statistical, explicit band
assert 0.4 < counts.get("11", 0) / 4000 < 0.6    # statistical, explicit band
```

### GHZ(3) acceptance test (reference)
```python
result = execute_circuit(ghz3_circuit, "ideal_qasm", shots=4000)
assert set(result.measurement_counts.keys()) <= {"000", "111"}  # deterministic
```

## 4. Current Automated Coverage (executed, not projected)

**33/33 tests passing**, as of this document's writing, via:
```bash
cd backend && pytest tests/ -v
```

| File | Tests | Representative assertions |
|---|---|---|
| `test_quantum_engine.py` | 13 | Bell/GHZ correctness, statevector norm/probabilities, noise increases outcome diversity, qubit-limit rejection, measurement-requirement rejection, validation rejections, logical-vs-transpiled gate/depth separation |
| `test_auth_api.py` | 6 | Register/duplicate/login success/failure, protected-endpoint 401s |
| `test_jobs_api.py` | 6 | Submit→results round-trip, invalid-circuit 422, status filter, cross-user 403, qubit-limit 422, unknown-job 404 |
| `test_circuits_and_algorithms_api.py` | 6 | Validate endpoint true/false paths, transpile endpoint, algorithm catalog completeness, Bernstein-Vazirani deterministic execution, cancellation + double-cancel 409 |
| `test_integration.py` | 1 (multi-assertion) | Full register→load→analyze→submit→poll→results→noise-sweep path |
| `conftest.py` | fixtures | Shared SQLite+fakeredis setup, auth header fixture |

CI (`\.github/workflows/ci.yml`) runs this suite on every push/PR
against a fresh SQLite database — no external services required,
matching the local test environment exactly.

## 5. Manual/E2E Verification Performed

Because no end-to-end browser test framework (Playwright/Cypress) is
wired into this project yet, the following was verified by live
browser automation during development and is **not** re-run
automatically on every change — a gap flagged for Release 2:

- Registration and login flow render and function correctly (dark
  theme, form validation, redirect to Dashboard).
- Circuit Lab: building a Bell circuit, resource analysis showing real
  depth/gate numbers, submitting and landing on a completed job with a
  correct histogram.
- Job Explorer and Job Details: filtering, histogram rendering,
  metadata display.
- Algorithm Library: catalog renders with all 7 algorithms.
- Noise Studio: a real sweep showing fidelity degrading from 1.0
  toward ~0.68 across 5 noise levels.

## 6. Test Types Required by the Original Brief, Mapped to Status

| Required test type | Status |
|---|---|
| Quantum Engine: gate construction | ✅ `test_quantum_engine.py` builds and executes Bell/GHZ circuits through the full gate dispatch table; `test_circuit_validation_rejects_wrong_param_count`/`test_circuit_validation_rejects_bad_qubit_index` cover malformed construction |
| Quantum Engine: Bell state correctness | ✅ |
| Quantum Engine: GHZ state correctness | ✅ |
| Quantum Engine: statevector normalization | ✅ |
| Quantum Engine: measurement probabilities | ✅ (via counts/shots sum + Bell 50/50 band) |
| Quantum Engine: noise model behaviour | ✅ (noisy leakage > ideal leakage) |
| Quantum Engine: circuit transpilation | ✅ |
| Backend: job submission | ✅ |
| Backend: job status transitions | ✅ (QUEUED visible pre-execution at the service layer test; COMPLETED visible via API) |
| Backend: successful execution | ✅ |
| Backend: failed execution | ✅ (invalid circuit → 422 before queuing; engine-level `QuantumExecutionError` paths covered by `test_shots_backend_requires_measurements`) |
| Backend: cancellation | ✅ |
| Backend: invalid circuit rejection | ✅ |
| Backend: result persistence | ✅ (implicit in submit→results round-trip) |
| API: authentication | ✅ |
| API: authorization | ✅ |
| API: input validation | ✅ |
| API: job submission | ✅ |
| API: result retrieval | ✅ |
| API: unauthorized job access | ✅ |
| Integration: real circuit through API→worker→results, no mocks | ✅ |

## 7. Known Gaps (explicitly not claimed as done)

1. **No execution-timeout test** — `JOB_EXECUTION_TIMEOUT_SECONDS` is
   configured but no test deliberately constructs a job that exceeds
   it and asserts the resulting `FAILED` transition.
2. **No worker-crash/retry test** — FR-JOB-008 (retry on transient
   failure) is unimplemented, so there is nothing to test yet.
3. **No load/concurrency test** — single-request latency was observed
   informally; no test exercises concurrent job submission at scale.
4. **No browser-level automated E2E suite** — §5's verification was
   manual/interactive, not committed as a repeatable Playwright/Cypress
   suite.
5. **No test asserts that an unexpected 500 never leaks internal
   exception detail** (API_SPECIFICATION.md's cross-cutting error
   format note).
6. **Docker Compose stack has not been tested end-to-end** on real
   Postgres/Redis (no Docker available in this environment) — see
   `RISK_REGISTER.md` R-INFRA-001.

These are carried into `ROADMAP.md` as explicit follow-up items, not
silently dropped.
