# RISK_REGISTER.md — Technical Risks and Mitigations

| ID | Risk | Probability | Impact | Mitigation | Owner/module |
|---|---|---|---|---|---|
| R-MEM-001 | **Exponential statevector memory growth.** A statevector simulation needs 2ⁿ complex amplitudes; a careless request (e.g., 40 qubits) could exhaust worker memory. | Medium (any user can type a large number) | High (could crash a worker process) | Hard ceiling `MAX_QUBITS_STATEVECTOR` (default 20) enforced in `engine.py::_check_qubit_limits` *before* simulation starts, and again in `job_service.create_job` before enqueueing. | Quantum Execution Engine |
| R-PERF-001 | **Quantum simulation computational cost.** Shot-based simulation of deep, highly-entangling circuits (e.g., many CNOTs/qubits) can take seconds to tens of seconds even in simulation — observed directly in the sibling QML benchmark project in this workspace, where a 4-qubit circuit at depth 3 took ~20s to build a kernel matrix on the same Aer simulator. | High (inherent to the domain) | Medium (slow jobs, not incorrect ones) | Async job model (Release 1) already decouples this from the API's responsiveness; `MAX_QUBITS_SHOTS`/`MAX_SHOTS` limits bound the worst case; execution/transpile timings are always reported so slowness is visible, not silent. | Quantum Execution Engine, Job Management |
| R-QUEUE-001 | **Queue overload.** Many simultaneous large jobs could back up the Redis queue faster than workers drain it. | Medium (depends on usage pattern) | Medium (delayed jobs, not lost ones — RQ persists queued jobs in Redis) | Horizontal worker scaling is architecturally free (independent RQ consumers); **not yet load-tested** to find the actual breaking point — tracked in ROADMAP.md P2. | Infrastructure |
| R-WORKER-001 | **Worker failures mid-job.** A worker crash while `RUNNING` could leave a job stuck. | Low-Medium | Medium (a stuck job looks like a hang to the user) | `job_timeout` configured per job; RQ's own timeout mechanism should eventually mark it failed. **Not yet verified by an automated test** — the single largest reliability gap in this register. | Job Management / Workers |
| R-NOISE-ACCURACY | **Noise model inaccuracy / misleading realism.** `qiskit_aer.noise` models are illustrative (parameterized depolarizing/readout error), not calibrated to any real device's measured error rates. A user could mistake the Noise Studio's output for a prediction of real hardware behavior. | Medium (easy to over-interpret) | Medium (misleads users about "what real quantum computers do") | Every noise-related UI label and this document set explicitly calls these simulations, not hardware predictions; `fidelity_proxy` is explicitly labeled as a shot-statistics proxy, not true state fidelity (PRD §1.8, NFR §6.9). | Noise Studio / Documentation |
| R-SEC-001 | **Circuit validation vulnerabilities.** A malicious or malformed circuit JSON could attempt to trigger unexpected behavior (e.g., huge operation lists, deeply nested conditions, injection via gate names). | Low (no code execution path exists at all) | High if it did succeed | No `eval`/`exec`/dynamic import anywhere in the circuit-construction path (FR-QC-006); gate dispatch is a closed lookup table; every field is type- and range-checked in `validate_circuit_json` before any Qiskit object is built. | Circuit Lab / Security |
| R-STORAGE-001 | **Large result storage.** Persisting full statevectors for high-qubit-count jobs could grow the database unboundedly. | Medium (without a cap) | Medium | `MAX_STATEVECTOR_JSON_QUBITS=16` cap already implemented (`app/workers/tasks.py`) — statevectors above this are not persisted at all, only probabilities. | Database / Workers |
| R-QISKIT-001 | **Qiskit version compatibility.** Qiskit's API has broken backward compatibility across major versions. **This already happened twice during this project's own development**: `qiskit.execute()` was removed (Qiskit 1.0+), requiring `AerSimulator().run()` instead; `QuantumCircuit.c_if` was removed (Qiskit 2.x), requiring `qc.if_test(...)` for classically-conditioned gates (needed for teleportation). | High (demonstrated, not hypothetical) | Medium (breaks on upgrade, not silently wrong) | Exact versions pinned in `requirements.txt` (`qiskit==2.6.1`, `qiskit-aer==0.18.2`); any future upgrade must re-verify the engine against the new version's actual API (as this project's own process required) rather than assume documentation from an older version still applies. | Quantum Execution Engine |
| R-UX-001 | **Complexity of visual circuit editing.** A full drag-and-drop canvas (e.g., React Flow) has real integration complexity and was descoped in favor of a reliable grid/toolbar editor for this prototype (see PRD, Release 3 implementation notes). | Low (descoping already happened) | Low (a UX preference, not a correctness risk) | Current editor has full JSON interoperability (anything buildable via JSON is buildable via the UI's gate/qubit/angle controls), so no capability was lost, only the drag-and-drop interaction model. | Frontend |
| R-HW-001 | **Future hardware integration challenges.** A real provider (e.g., IBM Quantum) has queueing, cost, authentication, and timing characteristics (minutes-to-hours) very different from a local simulator. | Unknown (no hardware access to test against) | Unknown | `BACKEND_REGISTRY`/`execute_circuit` abstraction is designed to isolate this change (ARCHITECTURE.md §8), but this is an untested design, not a working integration — explicitly flagged as such, not claimed as solved. | Quantum Execution Engine (future) |
| R-INFRA-001 | **Docker Compose stack unverified end-to-end.** This development environment has no Docker, Postgres, or Redis installed. | Certain (already true) | Medium (could hide an environment-specific bug that SQLite/fakeredis substitution wouldn't surface) | Every individual piece was verified in isolation (Alembic migration applied to SQLite; FastAPI app smoke-tested; full browser walkthrough against SQLite+fakeredis); the Compose/Dockerfiles follow standard, conventional patterns (health checks, `depends_on: condition: service_healthy`) that reduce but do not eliminate this risk. Flagged in every relevant document rather than asserted as done. | Infrastructure |

## Explicit Technical Assumptions

1. PostgreSQL's JSON column behaves equivalently to SQLite's for this
   schema's purposes (no Postgres-specific JSONB operators are used
   anywhere in the current code) — **assumption, not yet verified**.
2. A single RQ worker process is sufficient for the expected prototype
   usage (a handful of concurrent users); no multi-worker load test
   has been run to confirm or refute this.
3. `MAX_QUBITS_STATEVECTOR=20`/`MAX_QUBITS_SHOTS=30`/`MAX_SHOTS=100000`
   are reasonable starting defaults for a typical developer laptop's
   worker process, not derived from a formal capacity benchmark on the
   actual target deployment hardware.
4. JWT with a 24-hour expiry and no refresh-token flow is adequate for
   this product's session-length expectations (a working session, not
   a long-lived mobile app pattern).

## Unresolved Decisions

- Whether `experiment_runs.job_id` should become non-null (i.e.,
  whether noise-sweep points should become real queued jobs rather
  than synchronous inline executions) — currently always `null`
  (see DATABASE_DESIGN.md §2 `experiment_runs`).
- Whether API versioning (`/api/v1`) should be introduced now (clean
  break) or the unversioned paths should be kept and a `/api/v2` used
  for the *next* breaking change instead (avoiding a rename of
  existing, already-integrated endpoints). Not decided in this document
  — flagged for a product/engineering decision before Release 2's
  follow-up work begins.
