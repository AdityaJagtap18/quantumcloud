# QuantumCloud — A Mini Quantum Computing as a Service Platform

## 1. What QuantumCloud Is

QuantumCloud is a working prototype of a Quantum Computing as a Service
(QCaaS) platform: a web application where a user builds a quantum
circuit, submits it to a chosen simulation backend with configurable
shots and noise, watches it execute **asynchronously**, and inspects
real measurement results, probability distributions, and resource
statistics. Every number the frontend shows — job counts, histograms,
condition numbers, execution times — comes from an actual Qiskit Aer
simulation that ran during this session. Nothing is hardcoded.

## 2. Why QCaaS Platforms Exist

Quantum hardware is scarce, expensive, and (today) noisy and small. Real
QCaaS platforms (IBM Quantum, Amazon Braket, Azure Quantum) exist to
solve the same problem classical cloud computing solved for CPUs: let
many users share access to a limited resource through a managed queue,
with validation, resource accounting, and reproducible execution
records, without each user needing their own hardware. This project
reproduces that *workflow* — queueing, backend selection, noise
configuration, resource analysis, result storage — using classical
simulation as the backend, since this is a prototype rather than a
hardware integration.

## 3. Architecture and Service Boundaries

```
┌─────────────┐      REST (JWT)      ┌───────────────────────┐
│   Frontend   │ ───────────────────▶ │     FastAPI Backend    │
│ React + TS   │ ◀─────────────────── │                         │
└─────────────┘                      │  auth · circuits ·      │
                                      │  jobs · experiments ·   │
                                      │  algorithms · dashboard │
                                      └──────────┬──────────────┘
                                                  │
                             ┌────────────────────┼─────────────────────┐
                             ▼                    ▼                     ▼
                      ┌─────────────┐     ┌──────────────┐     ┌────────────────┐
                      │ PostgreSQL   │     │ Redis (RQ)   │     │ (sync fakeredis │
                      │ users, jobs, │     │ job queue    │     │  in dev/tests)  │
                      │ results, ... │     └──────┬───────┘     └────────────────┘
                      └─────────────┘            │
                                                  ▼
                                          ┌───────────────┐
                                          │ Worker process │
                                          │ (RQ consumer)  │
                                          └───────┬────────┘
                                                  ▼
                                   ┌───────────────────────────┐
                                   │  Quantum Execution Engine   │
                                   │  (Qiskit + Qiskit Aer)      │
                                   │  ideal · statevector ·      │
                                   │  noisy · custom_noise       │
                                   └───────────────────────────┘
```

**Service boundaries, deliberately kept separate:**
- The **API process** (`uvicorn app.main:app`) only validates requests,
  writes/reads the database, and enqueues work. It never runs a quantum
  circuit itself — `POST /api/jobs` returns as soon as the job is queued.
- The **worker process** (`python -m app.workers.worker_main`) is the
  only place `app/quantum/engine.py` is invoked for real job execution.
  This is what keeps the API responsive even if a simulation is slow.
- **PostgreSQL** is the system of record for jobs/results/experiments.
- **Redis** is purely the job queue transport (via [RQ](https://python-rq.org)).

## 4. Quantum Execution Lifecycle

1. User builds a circuit (visually or as JSON) and picks a backend.
2. `POST /api/jobs` validates the circuit JSON and backend/qubit/shot
   limits, creates a `QuantumJob` row with status `QUEUED`, and enqueues
   `execute_quantum_job(job_id)` on the `quantum_jobs` RQ queue.
3. A worker picks up the job: status → `VALIDATING` → circuit is rebuilt
   from JSON and checked again → status → `RUNNING`, `started_at` set →
   `app/quantum/engine.execute_circuit()` runs the real simulation →
   on success, a `QuantumResult` row is written and status → `COMPLETED`;
   on any validation or execution error, status → `FAILED` with
   `error_message` set, and no partial/incomplete result row is ever
   left behind (see `app/workers/tasks.py::_fail_job`).
4. The frontend polls `GET /api/jobs/{id}` (1.5s interval while
   `QUEUED`/`VALIDATING`/`RUNNING`) and then fetches
   `GET /api/jobs/{id}/results`.
5. `POST /api/jobs/{id}/cancel` is honored only while a job is still
   `QUEUED` or `VALIDATING` — once a worker has started running it,
   cancellation is refused (409) rather than silently lying about job
   state.

## 5. Simulator Architecture (Backend Registry)

Four backend types, implemented in `app/quantum/engine.py`, all on top
of `qiskit_aer.AerSimulator` — **these are simulators, not hardware**,
and the UI/API never claims otherwise:

| Backend | What it returns | Notes |
|---|---|---|
| `ideal_qasm` | Shot-based measurement counts | Noiseless |
| `statevector` | Exact amplitudes + probabilities + norm | No shots, no noise; qubit-limited by `MAX_QUBITS_STATEVECTOR` because memory is O(2ⁿ) |
| `noisy` | Shot-based counts | Preset noise level (low/medium/high) |
| `custom_noise` | Shot-based counts | Fully user-specified single/two-qubit gate error, measurement error, and error-type selection |

Noise types supported (`app/quantum/noise_models.py`): depolarizing,
bit-flip, phase-flip, amplitude damping, and readout error — each
built as a real `qiskit_aer.noise` object, not a cosmetic multiplier
on ideal results.

## 6. Quantum Circuit Transpilation

`app/quantum/analysis.py` reports resource usage **before and after**
transpilation, and keeps the two numbers visibly separate everywhere
(API response, DB, UI) specifically so logical and physical gate counts
are never confused:

- **Logical** (`analyze_logical_circuit`): qubits, clbits, total/1q/2q
  gate counts, depth, measurement count, width — computed directly on
  the circuit the user wrote.
- **Transpiled** (`analyze_transpiled_circuit`): depth, gate count,
  native gate distribution, SWAP overhead, and resource/depth overhead
  ratios, computed after `qiskit.transpile()` against a chosen coupling
  map (`fully_connected`, `linear`, `ring`, or a small `heavy_hex_like`
  example topology) — demonstrating how the same circuit's hardware
  cost changes with connectivity.

## 7. Quantum Noise Modeling

The Noise Experimentation Studio (`app/services/experiment_service.py`)
runs one circuit across several noise levels, each built into a real
`NoiseModel` (depolarizing + readout, scaled by the sweep parameter),
and compares every noisy run against a 4000-shot ideal baseline using
**total variation distance** between the two measurement distributions.
`fidelity_proxy = 1 − TVD` is explicitly labeled as a shot-statistics
proxy, not a true quantum state fidelity (which would require
statevector access) — see the Limitations section.

## 8. Job Queue Design

`app/workers/queue.py` picks between two modes based on `REDIS_URL`:
- **Production (Docker):** a real Redis connection with `is_async=True`
  — jobs are only executed when a separate `worker` container's RQ
  consumer picks them up, matching the brief's "API must never block"
  requirement for real deployments.
- **Local/test (`REDIS_URL=fakeredis://`):** an in-memory `fakeredis`
  connection with `is_async=False` — `queue.enqueue()` runs the job
  function synchronously, in-process. This exists because this
  environment has no Docker/Redis installed; it is not a mock of the
  quantum engine (that still runs for real), only a stand-in for the
  message broker. See [Running Without Docker](#11-running-without-docker-what-was-verified-here).

## 9. Resource Analysis

See §6. Every qubit/shot limit (`MAX_QUBITS_STATEVECTOR`,
`MAX_QUBITS_SHOTS`, `MAX_SHOTS`) is enforced at job-submission time in
`app/services/job_service.py`, *before* anything is queued, so an
oversized request fails fast with a 422 instead of silently queuing an
expensive or impossible simulation.

## 10. API Documentation

Interactive OpenAPI docs are served at `/docs` once the backend is
running. Summary of implemented endpoints:

```
POST   /api/auth/register
POST   /api/auth/login
GET    /api/backends
GET    /api/backends/{backend_id}
POST   /api/circuits/validate
POST   /api/circuits/analyze
POST   /api/circuits/transpile
POST   /api/jobs
GET    /api/jobs
GET    /api/jobs/{job_id}
POST   /api/jobs/{job_id}/cancel
GET    /api/jobs/{job_id}/results
POST   /api/experiments
GET    /api/experiments
GET    /api/experiments/{experiment_id}
POST   /api/experiments/{experiment_id}/run
GET    /api/algorithms
GET    /api/algorithms/{algorithm_id}
POST   /api/algorithms/{algorithm_id}/load
GET    /api/dashboard/stats
GET    /health
```

### Example: submit a Bell state job

```bash
TOKEN=$(curl -s -X POST localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo@quantumcloud.dev","password":"password123"}' | jq -r .access_token)

BACKEND_ID=$(curl -s localhost:8000/api/backends -H "Authorization: Bearer $TOKEN" \
  | jq -r '.[] | select(.backend_type=="ideal_qasm") | .id')

curl -s -X POST localhost:8000/api/jobs \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d "{
    \"circuit\": {
      \"num_qubits\": 2, \"num_clbits\": 2,
      \"operations\": [
        {\"gate\": \"h\", \"qubits\": [0]},
        {\"gate\": \"cx\", \"qubits\": [0, 1]},
        {\"gate\": \"measure\", \"qubits\": [0], \"clbits\": [0]},
        {\"gate\": \"measure\", \"qubits\": [1], \"clbits\": [1]}
      ]
    },
    \"backend_id\": \"$BACKEND_ID\",
    \"shots\": 2000
  }"
```

## 11. Installation and Execution

### With Docker (the primary, intended path)

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
docker compose up --build
```

Frontend: http://localhost:5173 · Backend docs: http://localhost:8000/docs

Development mode (hot reload for both services):
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Database migrations run automatically on backend container start
(`backend/entrypoint.sh` → `alembic upgrade head`). To run them manually:
```bash
docker compose exec backend alembic upgrade head
```

> **This repository's development machine had no Docker, Postgres, or
> Redis installed.** The Compose files, Dockerfiles, and Alembic
> migration above are written and were validated piece-by-piece (the
> migration was generated and applied against SQLite, whose DDL
> SQLAlchemy/Alembic generate identically in shape to Postgres for this
> schema), but `docker compose up` itself has **not** been run end to
> end on real Postgres/Redis containers. If you have Docker, that is
> the first thing to verify.

### Without Docker (verified in this environment)

```bash
# Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
DATABASE_URL="sqlite:///./dev.db" REDIS_URL="fakeredis://" JWT_SECRET_KEY="dev-secret" \
  uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
VITE_API_BASE_URL=http://localhost:8000 npm run dev
```

This is exactly how the screenshots below were produced.

## 12. Testing

```bash
cd backend
pytest tests/ -v
```

**33 tests, all passing**, covering:
- **Quantum engine** (`test_quantum_engine.py`): Bell/GHZ correctness,
  statevector normalization and exact Bell probabilities, noise
  measurably increasing outcome leakage, qubit/measurement limit
  enforcement, circuit validation rejections, logical-vs-transpiled
  gate/depth tracking.
- **Auth API** (`test_auth_api.py`): registration, duplicate rejection,
  login success/failure, unauthenticated/garbage-token rejection.
- **Jobs API** (`test_jobs_api.py`): submission → real execution →
  result retrieval, invalid circuit rejection, status filtering,
  cross-user access rejection (403), qubit-limit rejection, 404 on
  unknown job.
- **Circuits & algorithms API** (`test_circuits_and_algorithms_api.py`):
  validate/analyze/transpile endpoints, all 7 algorithms listed,
  Bernstein-Vazirani deterministically recovering its secret through
  the full job pipeline, and job cancellation (including the
  already-terminal double-cancel rejection).
- **Integration test** (`test_integration.py`): register → login → load
  an algorithm → analyze it → submit as a real job → poll → fetch real
  measurement results → run a noise sweep and check fidelity trends —
  **no quantum execution is mocked anywhere in this path.**

`REDIS_URL=fakeredis://` makes the queue synchronous for tests (see §8)
so every test observes the job's true final state without needing a
separate worker process or sleep/poll loop.

## 13. Known Limitations

- **No live Docker/Postgres/Redis verification.** See §11 — the
  infrastructure is written to spec but only individually validated.
- **`fidelity_proxy` in the Noise Studio is a shot-statistics proxy**
  (1 − total variation distance), not a true quantum state fidelity,
  which would require statevector access unavailable on shot-based
  backends. This is stated in the UI, not just here.
- **No real quantum hardware.** Every backend is a classical simulation
  on `qiskit_aer`. The UI/README never claim otherwise.
- **Statevector storage is size-limited** (`MAX_STATEVECTOR_JSON_QUBITS
  = 16` in `app/workers/tasks.py`) — beyond that, the statevector is
  simply not persisted to avoid unbounded JSON blobs in Postgres, per
  the brief's instruction to define a retention limit.
- **Circuit editor is a structured gate-by-gate builder**, not a
  drag-and-drop canvas (the brief allows React Flow "where useful";
  given the time budget, a reliable grid/wire editor with full JSON
  interoperability was prioritized over a canvas library integration).
- **Job cancellation is only guaranteed before a job starts running**
  (§4) — once a worker has started a simulation, it runs to completion
  or timeout; this is stated explicitly in the 409 response rather than
  faked.
- **Rate limiting** is a minimal fixed-window counter in Redis/fakeredis,
  not a production-grade token-bucket implementation.

## 14. Future Hardware Integration

`app/quantum/engine.py`'s `BACKEND_REGISTRY` and `execute_circuit()`
dispatch are the seam for this: a real hardware provider would be added
as a fifth `backend_type` (e.g. `ibm_quantum`) whose branch in
`execute_circuit` submits to that provider's SDK instead of
`AerSimulator`, while the job lifecycle, API, database schema, and
frontend are entirely unchanged — they already only depend on
`ExecutionResult`'s shape, not on how it was produced. Coupling-map
transpilation (§6) already demonstrates the hardware-connectivity
concept a real backend would need. Authentication/credentials for a
cloud quantum provider would be the main new piece of plumbing.

## 15. Project Structure

```
quantumcloud/
├── backend/
│   ├── app/
│   │   ├── api/            # FastAPI routers (auth, backends, circuits, jobs, experiments, algorithms, dashboard)
│   │   ├── algorithms/      # Prebuilt algorithm library (library.py)
│   │   ├── core/            # config.py, security.py
│   │   ├── db/               # SQLAlchemy session/base
│   │   ├── models/           # ORM models
│   │   ├── quantum/          # circuit_builder, noise_models, engine, analysis
│   │   ├── schemas/          # Pydantic request/response models
│   │   ├── services/         # business logic between API and engine/DB
│   │   └── workers/          # RQ queue, task function, worker entrypoint
│   ├── alembic/               # DB migrations
│   ├── tests/                 # 33 tests (see §12)
│   ├── Dockerfile / Dockerfile.worker / entrypoint.sh
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/         # axios client + typed endpoint functions
│   │   ├── components/  # Layout, CircuitEditor, StatusPill, States
│   │   ├── context/      # AuthContext, ThemeContext
│   │   ├── pages/         # Dashboard, CircuitLab, JobExplorer, JobDetails, NoiseStudio, AlgorithmLibrary, Login
│   │   └── types/
│   └── Dockerfile / Dockerfile.dev / nginx.conf
├── docker-compose.yml
├── docker-compose.dev.yml
└── .github/workflows/ci.yml
```

## 16. Definition-of-Done Checklist

| Requirement | Status |
|---|---|
| Launch via Docker Compose | Written, not live-verified (no Docker here) — see §11 |
| Register and log in | ✅ Verified in browser |
| Build a Bell circuit visually | ✅ Verified in browser |
| Submit to ideal QASM simulator | ✅ Verified in browser |
| Asynchronous job execution | ✅ Real RQ-based lifecycle; synchronous transport locally (§8) |
| Real measurement counts + histogram | ✅ Verified in browser (514/1024 "11", rest "00") |
| Noisy backend + ideal/noisy comparison | ✅ Verified via Noise Studio sweep |
| Circuit depth / gate count / transpile overhead | ✅ Verified in browser (Circuit Lab analysis panel) |
| Previous job results accessible | ✅ Job Explorer + Job Details |
| Run a prebuilt algorithm | ✅ Verified (Bernstein-Vazirani → deterministic "101") |
| Export results | ✅ JSON/CSV export on Job Details |
| Automated tests pass | ✅ 33/33 passing |
