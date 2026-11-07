# PRD: QuantumCloud — A Quantum Computing as a Service (QCaaS) Platform

**Status:** Draft v1.0
**Owner:** Product/Engineering (single-team project)
**Audience:** Engineering team implementing or extending QuantumCloud

> **Note on provenance.** A working prototype of this product already
> exists in this repository (`quantumcloud/backend`, `quantumcloud/frontend`)
> and has been manually and automatically tested (33 backend tests
> passing; a live browser walkthrough of registration, circuit
> building, execution, and noise sweeps). This PRD is written as a
> forward-looking requirements specification, as instructed, but where
> a requirement is already implemented and verified, this is called out
> explicitly in **Section 12 (MVP Definition)** and
> `REQUIREMENTS_TRACEABILITY.md`, so the document stays honest about
> what is specified vs. what is proven to work.

---

## 1. Product Analysis

### 1.1 What problem does QuantumCloud solve?

Running a quantum circuit in a Jupyter notebook with raw Qiskit answers
"does this circuit work," but it does not answer the questions a team
actually has when quantum workloads move beyond a single researcher's
laptop:

- Who submitted this job, and can they see it again next week?
- What backend and noise assumptions produced this result?
- How expensive (qubits, depth, gates, time) was this circuit, before
  and after it was adapted to a specific hardware topology?
- How does this result change if I inject hardware-realistic noise,
  systematically, rather than by hand-editing a script?
- Can a non-Qiskit-fluent teammate (a PM, a student, a hardware
  engineer) submit and inspect a circuit without writing Python?

QuantumCloud solves the **operational and collaborative** gap between
"a quantum circuit runs" and "quantum workloads are manageable,
inspectable, and reproducible by more than one person," by wrapping
quantum simulation in the same operational model (auth, job queue,
async execution, persisted history, REST API) that real QCaaS
platforms (IBM Quantum Platform, Amazon Braket, Azure Quantum) use for
actual hardware.

### 1.2 Intended users

See Section 3 (Personas) for full detail. Summary: students learning
quantum computing, researchers iterating on algorithms, software
developers integrating quantum execution into other systems, and
educators demonstrating concepts to a class.

### 1.3 Core value proposition

**One deployable system that turns "I have a Qiskit circuit" into "I
have a shareable, queryable, multi-user record of how that circuit
behaves across backends, noise levels, and hardware topologies" —
without requiring every user to install Python, Qiskit, or manage
their own simulator.**

### 1.4 What makes this different from a basic Qiskit notebook?

| Capability | Qiskit notebook | QuantumCloud |
|---|---|---|
| Multi-user isolation | ❌ (single local kernel) | ✅ per-user job ownership (FR-AUTH, FR-JOB) |
| Persistent job history | ❌ (lost when kernel restarts) | ✅ PostgreSQL-backed (FR-DB) |
| Non-blocking execution | ❌ (notebook cell blocks) | ✅ async queue + worker (FR-JOB-003) |
| Remote/API access | ❌ (local only, unless you build it) | ✅ REST API, versioned (FR-API) |
| Systematic noise sweeps | Manual, ad hoc | ✅ first-class Noise Studio module (FR-NOISE) |
| Resource/transpilation comparison UI | Manual `print()` + re-run | ✅ before/after resource analysis (FR-RES) |
| No-code circuit entry | ❌ | ✅ visual circuit lab + structured JSON (FR-QC) |
| Reproducibility record | Whatever the notebook happened to save | ✅ every job stores its exact circuit, backend, noise config, and timestamps |

### 1.5 Capabilities essential for a working QCaaS platform

1. User identity and per-user job isolation.
2. A circuit representation that is validated, not merely "whatever
   Python object the user typed," so the system can safely accept
   circuits from untrusted or non-expert input.
3. A backend abstraction so "which simulator/hardware ran this" is a
   first-class, swappable concept, not hardcoded.
4. A job model with an explicit lifecycle (QUEUED → VALIDATING →
   RUNNING → COMPLETED/FAILED/CANCELLED) and a queue, so execution is
   decoupled from the request/response cycle.
5. Persisted, retrievable results, with enough metadata to know what
   produced them.
6. Resource/cost visibility (qubits, gates, depth) *before and after*
   any hardware-aware transformation (transpilation), since this is
   the actual constraint real quantum hardware imposes.
7. A way to compare backends/noise conditions against each other, not
   just view one result in isolation.

### 1.6 What belongs in the MVP vs. later

See Section 12 for the full three-release breakdown. In short: the MVP
is "can a user reliably get a real measurement result from a real
circuit, asynchronously, with a persistent record" — noise realism,
transpilation-aware analysis, and the algorithm library are valuable
but not required to prove the core operational model, so they are
Release 2/3.

### 1.7 Functional platform vs. a results dashboard

QuantumCloud is explicitly **not** a dashboard that renders
precomputed or hardcoded numbers. Every acceptance criterion in this
document that involves a "result" (a count, a histogram, a fidelity
value, a depth number) requires that value to originate from an actual
Qiskit/Qiskit Aer execution or analysis call triggered by that specific
request — see FR-ENG-* and the Testing Strategy's ban on fabricated
results. A build that returns static JSON for `/api/jobs/{id}/results`
would fail acceptance regardless of how polished its UI looks.

### 1.8 Technical risks, complexity, dependencies (summary)

Full detail in `RISK_REGISTER.md`. Headline risks: statevector memory
is exponential in qubit count (hard qubit ceiling required); quantum
simulation is CPU-expensive and queue/worker capacity must be sized
accordingly; Qiskit's API has broken backward compatibility across
major versions (observed directly during this project: `qiskit.execute()`
removed, `QuantumCircuit.c_if` removed in favor of `if_test`) so pinning
and verifying against the installed version is mandatory, not optional;
noise models are illustrative, not calibrated to real hardware, and
must never be presented as such.

---

## 2. Scope Boundary

In scope: everything in Sections 4–11 below, as implemented by the
modules A–I. Out of scope for this PRD: billing/metering, multi-tenant
organizational hierarchies, real quantum hardware provider contracts,
mobile native apps.

(Sections 3–16 continue in this document; detailed functional
requirements, APIs, database design, and diagrams are split into the
companion documents listed in `README.md` under "Specification
Documents" to keep each document reviewable on its own — this is a
deliberate information-architecture choice, not a scope reduction.)

---

## 3. Target Users and Personas

### Persona 1: Quantum Computing Student

- **Goals:** Build intuition for how gates compose into algorithms;
  see real measurement statistics instead of only textbook math.
- **Main activities:** Load a prebuilt algorithm (Bell, GHZ, Grover),
  run it, compare the histogram to the textbook prediction.
- **Pain points:** Local Qiskit installation issues; not knowing
  whether a confusing result is "my circuit is wrong" or "noise/shots
  are too low"; no persistent place to keep past experiments across
  study sessions.
- **Expected capabilities:** Algorithm Library with explanations
  (FR-ALG-*), a circuit editor that doesn't require writing Python
  (FR-QC-*), clear ideal-vs-noisy distinction (FR-BE-*, FR-NOISE-*).
- **Typical journey:** Journey 4 in `USER_FLOWS.md` (load Grover,
  execute, inspect histogram against the expected marked state).

### Persona 2: Quantum Algorithm Researcher

- **Goals:** Rapidly iterate on a novel circuit; understand how noise
  and transpilation to a target topology degrade a specific
  algorithm's performance; keep a reproducible record of each
  configuration tested.
- **Main activities:** Submit many variants of a circuit, compare
  resource overhead and fidelity across configurations, export raw
  results for offline analysis (e.g., into the sibling QML benchmark
  project in this workspace).
- **Pain points:** Manually tracking which notebook cell produced
  which number; no systematic noise sweep tooling in plain Qiskit;
  losing track of backend/noise parameters used for a given plot.
- **Expected capabilities:** Resource analysis before/after
  transpilation (FR-RES-*), Noise Experimentation Studio with sweeps
  (FR-NOISE-*), JSON/CSV export (FR-RESULT-007), experiment history
  (FR-EXP-*).
- **Typical journey:** Journey 3 (resource inspection) and Journey 2
  (noisy vs. ideal comparison) in `USER_FLOWS.md`.

### Persona 3: Quantum Software Developer

- **Goals:** Integrate quantum circuit execution into a larger
  application or pipeline without hand-rolling job queueing, auth, or
  a simulator wrapper.
- **Main activities:** Calls the REST API directly (not the UI) to
  submit circuits programmatically, polls job status, retrieves
  results as JSON for downstream processing.
- **Pain points:** Undocumented or inconsistent APIs; unclear error
  semantics (was my circuit invalid, or did the backend fail?);
  no API versioning, so integrations break silently on upgrade.
- **Expected capabilities:** A versioned, documented REST API
  (FR-API-*, `/api/v1/...`), explicit error responses distinguishing
  validation failures (422) from execution failures (job `FAILED`
  status with `error_message`), OpenAPI docs.
- **Typical journey:** Programmatic equivalent of Journey 1, driven
  entirely through `curl`/SDK calls, as shown in `API_SPECIFICATION.md`.

### Persona 4: Quantum Computing Educator

- **Goals:** Demonstrate concepts live to a class; let students
  experiment hands-on without each needing a local Qiskit setup;
  show the *operational* reality of quantum computing (queues, noise,
  hardware constraints), not just the math.
- **Main activities:** Projects the Circuit Lab or Noise Studio live;
  assigns students accounts to run their own jobs; uses the Algorithm
  Library as lecture material.
- **Pain points:** Classroom Wi-Fi/laptop setup friction; students'
  individual environments diverging; no simple way to show "same
  circuit, different noise" side by side.
- **Expected capabilities:** Multi-user auth so each student has an
  isolated history (FR-AUTH-*), a browser-only experience (no local
  install), the Noise Studio's side-by-side comparison charts.
- **Typical journey:** Journey 2, performed live, then assigned as a
  follow-up exercise to students individually.

---

## 4. Product Scope — Modules

Modules A–I are defined in detail across the companion documents:

- **Module A (User Management):** `API_SPECIFICATION.md` §Auth,
  `DATABASE_DESIGN.md` §users.
- **Module B (Quantum Circuit Lab):** `API_SPECIFICATION.md` §Circuits,
  functional requirements FR-QC-*.
- **Module C (Backend Management):** functional requirements FR-BE-*,
  `ARCHITECTURE.md` §Backend Abstraction.
- **Module D (Job Management):** functional requirements FR-JOB-*,
  `USER_FLOWS.md` sequence diagrams.
- **Module E (Execution Engine):** functional requirements FR-ENG-*,
  `ARCHITECTURE.md` §Quantum Execution Engine.
- **Module F (Resource Analysis):** functional requirements FR-RES-*.
- **Module G (Execution Results):** functional requirements FR-RESULT-*.
- **Module H (Noise Experimentation Studio):** functional requirements
  FR-NOISE-*.
- **Module I (Algorithm Library):** functional requirements FR-ALG-*,
  with each algorithm's spec below.

### Module I detail: Algorithm Library contents

| Algorithm | Purpose | Expected input | Circuit construction | Execution parameters | Expected output |
|---|---|---|---|---|---|
| Bell State | Demonstrate 2-qubit entanglement | None (fixed) | H(q0); CX(q0,q1) | ideal_qasm, ≥1000 shots | ~50/50 split over {00, 11} |
| GHZ State | Generalize Bell to n qubits | n (default 3) | H(q0); CX chain | ideal_qasm, ≥1000 shots | ~50/50 split over {0…0, 1…1} |
| Quantum Teleportation | Demonstrate state transfer via entanglement + classical correction | None (teleports \|+⟩) | Bell pair + Bell-basis measurement + classically-conditioned X/Z | ideal_qasm | Uniform distribution over all 8 three-bit outcomes (see note below) |
| Deutsch-Jozsa | Determine constant vs. balanced function in one query | Oracle type (constant/balanced), n | Oracle as CNOT fan-out or identity | ideal_qasm | All-ones register for the implemented balanced oracle |
| Bernstein-Vazirani | Recover hidden n-bit secret in one query | Secret string | Oracle CNOTs per secret bit | ideal_qasm | Deterministic: secret string with probability 1 |
| Grover Search (2-qubit) | Amplify a marked 2-bit item | Target bitstring | Oracle (phase flip) + diffuser, 1 iteration | ideal_qasm | Target bitstring with probability 1 (exact for n=2, 1 iteration) |
| Quantum Fourier Transform | Apply QFT to an input register | n (default 3) | H + controlled phase rotations + swaps | ideal_qasm or statevector | Starting from \|000⟩: uniform superposition |

> Note on teleportation: because the corrected qubit is measured
> directly in the Z basis rather than rotated into the basis that
> would reveal the teleported `|+⟩` state deterministically, the
> *visible* acceptance criterion is "all 8 outcome combinations occur
> with ~equal frequency" (consistent with a correctly teleported `|+⟩`
> state), not a single deterministic bitstring. A future release should
> add an optional basis-rotation step before the final measurement to
> make teleportation fidelity directly observable (tracked as a
> Release 3 enhancement in `ROADMAP.md`).

---

## 5. Functional Requirements

Format per requirement: ID, description, priority (MoSCoW mapped to
P0–P3: P0=Must, P1=Should, P2=Could, P3=Won't-this-release), user
story, acceptance criteria, dependencies, verification method.

### Module A — User Management

**FR-AUTH-001** — User registration
- *Description:* The system shall allow a new user to register with an
  email and password.
- *Priority:* P0 (Must)
- *User story:* As a new user, I want to create an account so that I
  can submit jobs under my own identity.
- *Acceptance criteria:* `POST /api/v1/auth/register` with a valid
  unique email and password ≥8 characters returns `201` and a user
  record with no `password` or `password_hash` field in the response.
  A duplicate email returns `409`.
- *Dependencies:* `users` table (DATABASE_DESIGN.md).
- *Verification:* Automated API test (`test_auth_api.py::test_register_new_user`,
  `::test_register_duplicate_email_rejected`) — **implemented, passing**.

**FR-AUTH-002** — User login
- *Description:* The system shall authenticate a user by email and
  password and issue a signed access token.
- *Priority:* P0
- *User story:* As a registered user, I want to log in so I can access
  my jobs.
- *Acceptance criteria:* Correct credentials return `200` with a JWT;
  incorrect credentials return `401` without revealing which field was
  wrong.
- *Dependencies:* FR-AUTH-001.
- *Verification:* `test_auth_api.py::test_login_success`,
  `::test_login_wrong_password_rejected` — **implemented, passing**.

**FR-AUTH-003** — Authenticated access enforcement
- *Description:* The system shall require a valid access token on every
  endpoint except registration, login, backend listing, and algorithm
  listing/detail (public catalog data).
- *Priority:* P0
- *Acceptance criteria:* Any protected endpoint called without a token,
  or with an invalid/expired one, returns `401`.
- *Verification:* `test_auth_api.py::test_protected_endpoint_requires_auth`,
  `::test_protected_endpoint_rejects_garbage_token` — **implemented, passing**.

**FR-AUTH-004** — Per-user job/experiment isolation (authorization)
- *Description:* The system shall prevent a user from reading or
  cancelling another user's jobs or experiments.
- *Priority:* P0
- *Acceptance criteria:* Requesting another user's job by ID returns
  `403`, not `200` with the data or a silent `404`.
- *Verification:* `test_jobs_api.py::test_unauthorized_job_access_rejected` — **implemented, passing**.

**FR-AUTH-005** — User profile management
- *Description:* The system shall allow a user to view their own
  profile (email, creation date).
- *Priority:* P2 (Could — not required for core workflows)
- *Acceptance criteria:* `GET /api/v1/users/me` returns the
  authenticated user's own record.
- *Dependencies:* FR-AUTH-002.
- *Verification:* Not yet implemented — **planned, Release 3**. Current
  prototype exposes user identity only implicitly via job ownership,
  not a dedicated profile endpoint.

### Module B — Quantum Circuit Lab

**FR-QC-001** — Circuit structural validation
- *Description:* The system shall validate a circuit's JSON
  configuration (qubit/clbit counts, gate names, qubit index bounds,
  parameter counts) before constructing it.
- *Priority:* P0
- *Acceptance criteria:* An out-of-range qubit index, unknown gate
  name, or wrong parameter count is rejected with a specific error
  message identifying the offending operation index.
- *Verification:* `test_quantum_engine.py::test_circuit_validation_rejects_bad_qubit_index`,
  `::test_circuit_validation_rejects_wrong_param_count` — **implemented, passing**.

**FR-QC-002** — Rejection of invalid gate configurations at job submission
- *Description:* The system shall reject job submissions containing an
  invalid circuit before enqueueing, returning `422`.
- *Priority:* P0
- *Acceptance criteria:* `POST /api/v1/jobs` with an invalid circuit
  never creates a `QUEUED` row.
- *Dependencies:* FR-QC-001.
- *Verification:* `test_jobs_api.py::test_invalid_circuit_rejected` — **implemented, passing**.

**FR-QC-003** — Configurable circuit parameters
- *Description:* The system shall support a variable number of qubits,
  classical bits, and gate-specific parameters (e.g., rotation angles)
  per circuit.
- *Priority:* P0
- *Verification:* `CircuitConfig`/`CircuitOperation` schema
  (`API_SPECIFICATION.md`) — **implemented**.

**FR-QC-004** — Supported gate set
- *Description:* The system shall support, at minimum: I, X, Y, Z, H,
  S, T, RX, RY, RZ (single-qubit); CX, CZ, SWAP, CRX (multi-qubit);
  and measurement.
- *Priority:* P0
- *Acceptance criteria:* Each listed gate can be added via both the
  structured JSON format and (Release 3) the visual editor.
- *Verification:* `app/quantum/circuit_builder.py::SINGLE_QUBIT_GATES`,
  `MULTI_QUBIT_GATES` — **implemented**; UI coverage confirmed by
  manual browser walkthrough.

**FR-QC-005** — Classically-conditioned operations
- *Description:* The system shall support gates conditioned on a
  classical bit's measured value, to enable algorithms such as
  teleportation that require mid-circuit feed-forward.
- *Priority:* P1 (Should — required for Module I's teleportation
  algorithm, not for Release 1's Bell/GHZ scope)
- *Acceptance criteria:* A circuit JSON operation with a `condition`
  field applies only when that classical bit holds the specified value.
- *Verification:* `test_quantum_engine` teleportation round-trip in
  `app/algorithms/library.py` tests — **implemented, passing**.

**FR-QC-006** — No arbitrary code execution from circuit input
- *Description:* The system shall never evaluate or execute
  user-supplied strings as code when constructing a circuit.
- *Priority:* P0 (security-critical)
- *Acceptance criteria:* Circuit construction uses only an explicit
  gate-name-to-method lookup table; no `eval`/`exec`/dynamic import on
  user input anywhere in the request path.
- *Verification:* Code review of `app/quantum/circuit_builder.py`
  (`build_circuit` dispatches only through `SINGLE_QUBIT_GATES`/
  `MULTI_QUBIT_GATES` dictionaries) — **implemented**; also covered by
  Security Review in `TESTING_STRATEGY.md`.

**FR-QC-007** — Circuit resource/structure visualization
- *Description:* The system shall provide a visual representation of
  the circuit's qubit wires and placed gates.
- *Priority:* P1
- *Verification:* `CircuitEditor.tsx` wire rendering — **implemented**;
  confirmed via browser screenshot.

### Module C — Quantum Backend Management

**FR-BE-001** — Common backend interface
- *Description:* The system shall expose all registered simulation
  backends through a single interface (`execute_circuit(circuit,
  backend_type, shots, noise_config) -> ExecutionResult`) so new
  backends can be added without changing callers.
- *Priority:* P0
- *Verification:* `app/quantum/engine.py::BACKEND_REGISTRY`,
  `execute_circuit` — **implemented**; architectural review confirms no
  caller branches on backend type outside this module.

**FR-BE-002** — Ideal QASM simulator
- *Priority:* P0 — **implemented, tested** (`test_bell_state_correctness`).

**FR-BE-003** — Statevector simulator with qubit ceiling
- *Description:* The system shall provide exact statevector/probability
  results and shall refuse requests exceeding a configured qubit
  limit, since memory grows as 2ⁿ.
- *Priority:* P0
- *Acceptance criteria:* A request exceeding `MAX_QUBITS_STATEVECTOR`
  (default 20) is rejected with a clear error before simulation starts.
- *Verification:* `test_statevector_backend_rejects_too_many_qubits` — **implemented, passing**.

**FR-BE-004** — Noisy simulator (preset noise levels)
- *Priority:* P1 — **implemented, tested** (`test_noise_model_changes_distribution`).

**FR-BE-005** — Custom noise configuration
- *Description:* The system shall allow a user to specify
  single-qubit gate error, two-qubit gate error, measurement error,
  and which error types (depolarizing, bit-flip, phase-flip, amplitude
  damping, readout) to apply.
- *Priority:* P1 — **implemented, tested** (`test_custom_noise_config_requires_measurements_runs`).

**FR-BE-006** — Explicit simulator-vs-hardware distinction
- *Description:* The system shall never represent a simulator backend
  as physical quantum hardware in any API response, database record,
  or UI label.
- *Priority:* P0
- *Acceptance criteria:* Every backend's `description` field and every
  UI label referencing it includes "simulat" (simulator/simulation).
- *Verification:* `BACKEND_REGISTRY` descriptions; manual UI review — **implemented**.

**FR-BE-007** — Forward path for physical hardware backends
- *Description:* The backend abstraction shall be extensible to a
  future physical-hardware backend type without changes to the job
  API, job service, or database schema.
- *Priority:* P2 (Could — design requirement, not a working integration)
- *Verification:* Architectural review of `BACKEND_REGISTRY`/
  `execute_circuit` dispatch — **design verified**; no physical
  backend implemented (no hardware access in this project).

### Module D — Quantum Job Management

**FR-JOB-001** — Job submission
- *Description:* The system shall allow authenticated users to submit
  quantum circuit execution jobs.
- *Priority:* P0 — **implemented, tested** (`test_submit_job_and_retrieve_results`).

**FR-JOB-002** — Unique job identifiers
- *Priority:* P0 — **implemented** (UUID primary key, `app/models/models.py::gen_uuid`).

**FR-JOB-003** — Asynchronous background execution
- *Description:* The system shall execute accepted jobs asynchronously
  using background workers, and the job-submission API call shall not
  block for the duration of circuit execution.
- *Priority:* P0
- *Acceptance criteria:* `POST /api/v1/jobs` returns before a
  multi-second circuit simulation completes, in the production
  (real-Redis, `is_async=True`) queue configuration.
- *Verification:* `app/workers/queue.py` design (`is_async=True` for
  real Redis) — **implemented**; *not separately load-tested for
  concurrency in this environment* (see `RISK_REGISTER.md`).

**FR-JOB-004** — Job status exposure
- *Priority:* P0 — **implemented, tested** (`GET /api/v1/jobs/{id}`).

**FR-JOB-005** — Result persistence
- *Priority:* P0 — **implemented, tested** (`quantum_results` table, one row per completed job).

**FR-JOB-006** — Job cancellation (pre-execution only)
- *Description:* The system shall allow cancellation of a job only
  while it is `QUEUED` or `VALIDATING`; cancellation of a `RUNNING` job
  shall be refused with a clear error rather than silently ignored.
- *Priority:* P1
- *Verification:* `job_service.py::cancel_job`, tested in
  `test_circuits_and_algorithms_api.py::test_job_cancellation_before_execution` — **implemented, passing**.

**FR-JOB-007** — Execution timeout
- *Description:* The system shall enforce a maximum execution duration
  per job (`JOB_EXECUTION_TIMEOUT_SECONDS`), after which the job is
  marked `FAILED`.
- *Priority:* P1
- *Verification:* RQ `job_timeout` parameter set in `job_service.py::create_job` — **implemented**;
  *not exercised by an automated test that deliberately times out a
  job* (flagged as a coverage gap in `TESTING_STRATEGY.md`).

**FR-JOB-008** — Retry handling for transient worker failures
- *Description:* The system shall support retrying a job that failed
  due to a transient infrastructure error (e.g., a dropped DB
  connection), as distinct from a job that failed due to an invalid
  circuit (which must never be retried, since retrying won't fix it).
- *Priority:* P2 (Could)
- *Verification:* **Not implemented.** RQ supports retry policies
  natively; this is a configuration gap, not a redesign, tracked in
  `ROADMAP.md` Release 2 follow-up.

**FR-JOB-009** — No incomplete/inconsistent records on failure
- *Description:* A failed job shall never leave a `QuantumResult` row
  without a corresponding terminal job status, or vice versa.
- *Priority:* P0
- *Verification:* `app/workers/tasks.py::_fail_job` always sets status
  and timestamp together in one commit before any result row would be
  created — **implemented**; covered implicitly by
  `test_invalid_circuit_rejected` (no result row exists for a job that
  never reached `COMPLETED`).

### Module E — Quantum Execution Engine

**FR-ENG-001** — Qiskit circuit construction from validated JSON
- *Priority:* P0 — **implemented, tested.**

**FR-ENG-002** — Circuit transpilation against a coupling map
- *Priority:* P1 — **implemented, tested** (`test_transpilation_changes_gate_set_for_linear_topology`).

**FR-ENG-003** — Shot-based execution with accurate count aggregation
- *Description:* Returned measurement counts shall sum exactly to the
  requested shot count.
- *Priority:* P0 — **implemented, tested** (`test_measurement_counts_sum_to_shots`).

**FR-ENG-004** — Statevector execution with normalization guarantee
- *Description:* Returned statevector probabilities shall sum to 1
  within floating-point tolerance.
- *Priority:* P0 — **implemented, tested** (`test_statevector_normalization`).

**FR-ENG-005** — Noise model application
- *Priority:* P1 — **implemented, tested.**

**FR-ENG-006** — Qiskit version compatibility verification
- *Description:* The engine's use of Qiskit/Qiskit Aer APIs shall be
  verified against the actually-installed version, not assumed from
  documentation or prior versions.
- *Priority:* P0 (process requirement)
- *Verification:* Directly motivated by two breaking changes
  encountered and fixed during this project (`qiskit.execute()`
  removed in Qiskit 1.0+; `QuantumCircuit.c_if` removed in Qiskit 2.x
  in favor of `if_test`) — **process followed**; pin exact versions in
  `requirements.txt` (`qiskit==2.6.1`, `qiskit-aer==0.18.2`).

### Module F — Quantum Resource Analysis

**FR-RES-001..008** — Logical qubit/clbit count, total/1q/2q gate
count, depth, measurement count, width (pre-transpilation); transpiled
depth, transpiled gate count, native gate distribution, SWAP overhead,
resource/depth overhead ratios (post-transpilation).
- *Priority:* P1
- *Acceptance criteria:* Logical and transpiled numbers are reported
  as distinct fields in the same response, never merged or conflated.
- *Verification:* `test_logical_vs_transpiled_gate_counts_are_distinguished` — **implemented, passing**.

### Module G — Execution Results

**FR-RESULT-001** — Measurement counts — P0, **implemented, tested.**
**FR-RESULT-002** — Probability distributions — P0, **implemented, tested.**
**FR-RESULT-003** — Measurement histogram (UI) — P1, **implemented** (Recharts bar chart, `JobDetails.tsx`).
**FR-RESULT-004** — Statevector probabilities (statevector backend only) — P1, **implemented.**
**FR-RESULT-005** — Execution metadata (backend, shots, timings, noise) — P0, **implemented, tested.**
**FR-RESULT-006** — Circuit diagram display — P2, **partially implemented** (wire diagram in Circuit Lab; not yet duplicated on the Job Details page — gap, Release 3).
**FR-RESULT-007** — JSON/CSV export — P1, **implemented** (`JobDetails.tsx::exportJson/exportCsv`).
**FR-RESULT-008** — Historical comparison across jobs — P2, **not implemented** (single-job view only; cross-job comparison deferred to Release 3, see `ROADMAP.md`).

### Module H — Noise Experimentation Studio

**FR-NOISE-001** — Noise model configuration (preset or custom) — P1, **implemented, tested.**
**FR-NOISE-002** — Noise parameter sweep across a user-specified list of levels — P1, **implemented, tested** (`run_noise_sweep`).
**FR-NOISE-003** — Ideal-vs-noisy comparison baseline — P1, **implemented** (sweep always computes a 4000-shot ideal baseline).
**FR-NOISE-004** — Fidelity/observable-error metric per noise level — P1, **implemented**, labeled explicitly as a shot-statistics proxy (1 − total variation distance), not true quantum state fidelity — see `RISK_REGISTER.md` R-NOISE-ACCURACY.
**FR-NOISE-005** — Noise-vs-performance chart — P1, **implemented** (Recharts line chart, `NoiseStudio.tsx`).
**FR-NOISE-006** — Experiment history persistence — P1, **implemented** (`experiments`/`experiment_runs` tables); **list/detail UI not yet built** (API-only today — gap, Release 3).

### Module I — Quantum Algorithm Library

**FR-ALG-001** — Catalog of ≥7 named algorithms with description and
math intuition — P1, **implemented, tested** (`test_list_algorithms_returns_all`).
**FR-ALG-002** — Load algorithm into circuit editor — P1, **implemented** (verified via browser).
**FR-ALG-003** — Algorithms must be genuinely constructed and executed,
never represented by hardcoded output — P0, **implemented**: every
algorithm is built as a real `QuantumCircuit` in
`app/algorithms/library.py` and round-tripped through the same JSON
schema and execution engine as a user-authored circuit; verified by
`test_load_bernstein_vazirani_and_run_recovers_secret`, which asserts
the *actual* execution result (`{"101": 1000}`), not a stored value.

---

## 6. Non-Functional Requirements

### 6.1 Performance

| Requirement | Initial target | Status / basis |
|---|---|---|
| API response time (non-execution endpoints: auth, backend list, job status, dashboard stats) | p95 < 200ms on the reference dataset sizes used in testing | **Requires benchmarking under concurrent load; not yet measured.** Single-request latency observed informally during manual testing was well under this (SQLite, no concurrency). |
| Job submission latency (API call duration, not execution time) | < 300ms to return `202`-equivalent `201 QUEUED` | Directly measured as near-instant with a real async queue, since the endpoint only validates + writes + enqueues. **Not yet measured against real Redis under load.** |
| Job status retrieval latency | p95 < 150ms | Simple indexed primary-key lookup; **not yet load-tested.** |
| Background execution duration | Circuit- and backend-dependent; **not a fixed SLA.** Observed in this project: a 4-qubit Bell-like circuit on `ideal_qasm` completes in well under 100ms; a 4-qubit circuit on the ZZ-style heavy entangling feature map at depth 3 (from the sibling QML benchmark project, same Aer simulator) took ~20s for a ~70×70 kernel matrix — illustrating that execution time is dominated by circuit structure and shot/qubit count, not a constant. | Benchmark-derived from adjacent project in this workspace; QuantumCloud itself has not been benchmarked at scale. |
| Circuit resource limits | `MAX_QUBITS_STATEVECTOR=20`, `MAX_QUBITS_SHOTS=30`, `MAX_SHOTS=100000` (defaults) | **Implemented as hard limits**; the specific numeric values are starting points, not derived from a formal capacity study, and should be revisited once real worker hardware is sized (flagged assumption). |

**Explicitly avoided:** no claim of "the platform is fast" without a
number; no invented 99.99% uptime SLA for a single-team prototype.

### 6.2 Scalability

- The worker tier is horizontally scalable by running multiple RQ
  worker containers against the same Redis queue (no code change
  required — RQ workers are independent consumers).
- The API tier is stateless (JWT-based auth, no server-side session)
  and can run multiple replicas behind a load balancer.
- **Not yet addressed:** database connection pool sizing under
  concurrent load; Redis queue depth alerting; this is appropriate for
  a prototype but must be revisited before any production traffic
  (tracked in `RISK_REGISTER.md`).

### 6.3 Reliability

- **Worker failure handling:** if a worker process crashes mid-job, RQ
  (configured with a `job_timeout`) will eventually reclaim the job,
  but **no automated requeue-with-backoff policy is implemented yet**
  (FR-JOB-008 gap).
- **Job recovery:** a job stuck in `RUNNING` past its timeout should be
  marked `FAILED` by the queue's timeout mechanism; **this specific
  path (timeout → FAILED transition) has not been exercised by an
  automated test**, only by code inspection of RQ's `job_timeout`
  behavior.
- **Database consistency:** every status transition and its associated
  timestamp are written in the same commit (see FR-JOB-009); no
  multi-step transition is left partially applied.
- **Retry policy:** none implemented beyond RQ's defaults (no retry).
  This is a deliberate choice for Release 1/2 — retrying a job whose
  circuit is invalid would waste resources — but a transient-failure
  retry policy is a named gap (FR-JOB-008).

### 6.4 Security

- **JWT authentication:** HS256-signed tokens, 24h expiry by default
  (`JWT_EXPIRE_MINUTES`), secret key must be overridden in production
  (`.env.example` ships a placeholder that is clearly marked
  `CHANGE_ME_IN_PRODUCTION`).
- **Password hashing:** bcrypt via `passlib`, never stored or logged in
  plaintext.
- **User-level authorization:** enforced at the service layer
  (FR-AUTH-004), not just hidden in the UI.
- **Input validation:** every circuit is validated against an explicit
  schema before construction (FR-QC-001); no arbitrary code execution
  path exists (FR-QC-006).
- **Execution resource restrictions:** qubit and shot ceilings enforced
  before enqueueing (FR-BE-003, job_service limits).
- **Secrets management:** `.env` files are git-ignored; `.env.example`
  documents every variable without real values; no secret is baked
  into any Docker image layer.
- **Rate limiting:** a minimal fixed-window limiter
  (`rate_limit_dependency`) is in place but is explicitly **not**
  production-grade (no distributed token bucket, no per-endpoint
  tuning) — named limitation.

### 6.5 Maintainability

- Clear module boundaries (API / services / quantum engine / workers /
  models) with no circular dependencies; services never import from
  `app/api`.
- Alembic migrations version the schema instead of ad hoc DDL.
- Pinned dependency versions (`requirements.txt`, `package.json`) to
  avoid the kind of silent breakage described in FR-ENG-006.

### 6.6 Observability

- Structured logging via Python's `logging` module in the worker
  (`app.workers.tasks` logger) and API.
- **Not yet implemented:** centralized log aggregation, metrics
  export (e.g., Prometheus), distributed tracing. Acceptable for a
  prototype; flagged for any real deployment.

### 6.7 Usability

- Dark/light theme, loading/empty/error states on every data-fetching
  page (see `UI/UX Requirements` in `USER_FLOWS.md`).
- No-code circuit construction via the visual editor (Release 3).

### 6.8 Data Integrity

- Foreign keys enforce job→user, job→backend, result→job (1:1),
  experiment→user, experiment_run→experiment relationships
  (`DATABASE_DESIGN.md`).
- Statevector payloads are size-limited before persistence
  (`MAX_STATEVECTOR_JSON_QUBITS=16` in `app/workers/tasks.py`) to
  avoid unbounded JSON blob growth — a concrete, already-implemented
  retention control, not just a stated intention.

### 6.9 Reproducibility

- Every job row stores the *exact* circuit JSON, backend, shot count,
  and noise configuration used — the full input needed to reproduce a
  result is never inferred or reconstructed after the fact.
- Fixed library versions (Qiskit, Qiskit Aer) ensure the same circuit
  produces the same *distributional* behavior (shot noise aside) across
  runs, modulo any future intentional version upgrade.

---

## 7. System Architecture Requirements

See `ARCHITECTURE.md` for full detail, including all required Mermaid
diagrams (high-level architecture, component architecture, job
execution sequence, circuit submission sequence, ER diagram, deployment
architecture) and the explicit responsibility statement for each of:
Frontend (React/TS/Vite/Tailwind), Backend (FastAPI/SQLAlchemy/
Pydantic), Quantum Engine (Qiskit/Qiskit Aer), Infrastructure
(PostgreSQL/Redis/RQ/Docker/Compose).

## 8. Database Requirements

See `DATABASE_DESIGN.md` for the full conceptual data model, attributes,
types, keys, relationships, constraints, indexing, the ER diagram, and
the JSON/JSONB-vs-relational and statevector-retention decisions.

## 9. API Requirements

See `API_SPECIFICATION.md` for the full endpoint-by-endpoint contract
(method, path, purpose, request/response schema, auth requirement,
validation rules, error responses) under the `/api/v1` prefix, with
representative JSON examples.

## 10. User Experience and User Journeys

See `USER_FLOWS.md` for Journeys 1–4 (Bell execution, noisy comparison,
resource inspection, prebuilt-algorithm execution) with starting
conditions, actions, system responses, success/failure conditions, and
the specific API calls each journey makes.

## 11. UI/UX Requirements

See `USER_FLOWS.md` §UI/UX Requirements for the 9 screens (Dashboard,
Circuit Lab, Backend Selection, Job Explorer, Job Details, Results
Visualization, Noise Studio, Algorithm Library, User Settings) with
purpose, components, interactions, required backend data, and
loading/empty/error states for each.

---

## 12. MVP Definition — see also `ROADMAP.md`

### Release 1: Core QCaaS MVP

**Scope:** user auth; Bell/GHZ execution; ideal QASM + statevector
simulators; async job queue; job status tracking; measurement
visualization; PostgreSQL persistence; Docker Compose deployment.

**Dependencies:** none (foundational release).

**Deliverables:** `app/api/auth.py`, `app/quantum/engine.py`
(`ideal_qasm`, `statevector` backends only), `app/workers/*`,
`app/models/models.py` (users, quantum_jobs, quantum_results,
quantum_backends), `docker-compose.yml`.

**Acceptance criteria:**
1. A new user can register, log in, and receive a JWT (FR-AUTH-001..004).
2. A Bell-state circuit submitted to `ideal_qasm` returns measurement
   counts whose two observed bitstrings are `00`/`11` only, each
   between 40–60% of shots at ≥2000 shots (statistical tolerance per
   `TESTING_STRATEGY.md`).
3. A GHZ(3) circuit submitted the same way returns only `000`/`111`.
4. Job status transitions are observable via `GET /api/v1/jobs/{id}`
   and reach `COMPLETED` for valid circuits.
5. Restarting the API process does not lose previously completed job
   results (Postgres-backed).
6. `docker compose up --build` brings up all five services and the
   backend's `/health` endpoint returns `200`.

**Exit condition:** all six acceptance criteria pass in a clean
environment.

**Current implementation status:** ✅ Implemented and verified for all
items except item 6 (Docker Compose is written but not run on real
Postgres/Redis in this environment — see `ARCHITECTURE.md` §Verification
Status). Items 1–5 verified via automated tests and a live browser
session using SQLite + fakeredis substitutes.

### Release 2: Quantum Engineering Capabilities

**Scope:** noisy simulation; custom noise configuration; circuit
transpilation; resource analysis; backend comparison; noise
experimentation (sweeps).

**Dependencies:** Release 1 (job/backend model must exist first).

**Deliverables:** `app/quantum/noise_models.py`, `app/quantum/analysis.py`,
`app/services/experiment_service.py`, `experiments`/`experiment_runs`
tables, Noise Studio frontend page.

**Acceptance criteria:**
1. The same circuit run through `noisy` (high preset) shows measurably
   more outcome diversity than `ideal_qasm` (FR-NOISE-003).
2. `POST /api/v1/circuits/transpile` returns a different gate count
   or depth than `/analyze` for at least one non-trivial topology
   (e.g., `linear`) on a circuit requiring qubit routing.
3. A noise sweep across ≥3 levels produces a monotonically
   non-increasing fidelity-proxy trend within statistical tolerance.

**Exit condition:** all three criteria pass.

**Current implementation status:** ✅ Implemented and verified (see
`TESTING_STRATEGY.md` §Executed Results and the live Noise Studio
sweep showing fidelity dropping from 1.0 toward ~0.68 as noise
increased from 0.0 to 0.10).

### Release 3: Advanced Platform

**Scope:** visual circuit editor; algorithm library; experiment
management UI; advanced analytics; hardware provider abstraction
(interface only, no physical integration); future hardware
integration design.

**Dependencies:** Releases 1 and 2.

**Deliverables:** `CircuitEditor.tsx`, `app/algorithms/library.py`,
Algorithm Library + Noise Studio frontend pages, `BACKEND_REGISTRY`
designed to accept a 5th backend type without touching job/API/DB
layers (see `ARCHITECTURE.md` §Future Hardware Integration).

**Acceptance criteria:**
1. All 7 algorithms in §4 Module I load into the circuit editor and
   execute without error.
2. The circuit editor supports every gate in FR-QC-004's list via UI
   controls, not only via raw JSON.
3. `BACKEND_REGISTRY` and `execute_circuit()` are structured so that
   adding a new backend type requires no changes to
   `app/api/jobs.py`, `app/services/job_service.py`, or any DB
   migration (architectural review, not a runtime test).

**Exit condition:** all three criteria pass.

**Current implementation status:** ✅ Implemented and verified for
items 1–2 (Bernstein-Vazirani deterministically returns its secret
through the full pipeline in `test_circuits_and_algorithms_api.py`).
Item 3 verified by code review of `app/quantum/engine.py`'s dispatch
structure, not by adding a real hardware backend (no provider
available).

---

## 13. Testing Strategy

See `TESTING_STRATEGY.md` for the full test plan. Summary: unit tests
for circuit construction and kernel/engine correctness; API tests per
endpoint; integration tests exercising the full register→submit→
execute→retrieve path with no mocked quantum execution; explicit
deterministic acceptance tests for Bell/GHZ state preparation with
statistical tolerances stated numerically, not qualitatively.

## 14. Risks and Constraints

See `RISK_REGISTER.md` for the full risk register (probability,
impact, mitigation, owner per risk), covering exponential statevector
memory growth, simulation cost, queue overload, worker failures, noise
model inaccuracy, validation vulnerabilities, result storage growth,
Qiskit version compatibility, visual-editor complexity, and future
hardware integration.

## 15. Success Metrics

**Engineering quality metrics** (process/system health, independent of
quantum semantics):
- Job submission success rate (valid circuits accepted): target ≥99%
  of structurally-valid submissions reach `QUEUED` without a 5xx error.
- Job completion rate (`QUEUED` → `COMPLETED`, excluding jobs that are
  legitimately `FAILED` due to invalid circuits or `CANCELLED` by the
  user): target ≥98% for circuits within configured qubit/shot limits.
- Average API response time for non-execution endpoints: see §6.1.
- Worker failure rate (jobs lost to a worker crash rather than
  completing or reaching a clean `FAILED` state): target <1%; **not
  yet measurable — no chaos/failure-injection testing performed.**
- Automated test pass rate: **currently 33/33 (100%)** backend tests
  passing, as of this document's writing — the one number in this
  section that is not an estimate.
- Test coverage: not yet measured with a coverage tool; qualitatively,
  every module in `app/quantum/`, `app/services/`, and `app/api/` has
  at least one direct or integration-level test.

**Quantum computing metrics** (correctness/behavior of the quantum
execution itself):
- Circuit validation success rate: percentage of well-formed circuits
  (per FR-QC-001's schema) that validate successfully — target 100%
  for schema-conforming input, by construction.
- Reproducibility of execution results: for a fixed circuit, backend,
  and shot count on `ideal_qasm`, the *set of possible outcomes* must
  be identical run-to-run (e.g., Bell always yields only `{00, 11}`),
  even though shot-level frequencies vary — verified by
  `test_bell_state_correctness` across multiple invocations in CI.
- Successful end-to-end Bell circuit execution: **demonstrated live**
  in this project (514/1024 "11", rest "00" at 1024 shots).
- Successful ideal-vs-noisy experiment: **demonstrated live** (fidelity
  proxy dropping from 1.0 toward ~0.68 as noise increased 0.0→0.10).

## 16. Final PRD Deliverables

| # | Document | Status |
|---|---|---|
| 1 | `PRD.md` (this file) | ✅ |
| 2 | `ARCHITECTURE.md` | ✅ |
| 3 | `API_SPECIFICATION.md` | ✅ |
| 4 | `DATABASE_DESIGN.md` | ✅ |
| 5 | `USER_FLOWS.md` | ✅ |
| 6 | `TESTING_STRATEGY.md` | ✅ |
| 7 | `ROADMAP.md` | ✅ |
| 8 | `RISK_REGISTER.md` | ✅ |
| 9 | `REQUIREMENTS_TRACEABILITY.md` | ✅ |

All Mermaid diagrams (architecture, ER, job sequence) are embedded
in the documents above rather than as standalone files, so each
diagram stays next to the prose that explains it — cross-referenced
from this list.

---

## Related documents

- `ARCHITECTURE.md`, `API_SPECIFICATION.md`, `DATABASE_DESIGN.md`,
  `USER_FLOWS.md`, `TESTING_STRATEGY.md`, `ROADMAP.md`,
  `RISK_REGISTER.md`, `REQUIREMENTS_TRACEABILITY.md` — all in this
  `docs/` directory.
