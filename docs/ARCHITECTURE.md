# ARCHITECTURE.md — QuantumCloud Technical Architecture

## 1. Component Responsibilities

| Component | Technology | Responsibility | What it must NOT do |
|---|---|---|---|
| **Frontend** | React 19 + TypeScript + Vite + Tailwind CSS 4 | Render UI, collect user input (circuit, backend, noise config), call the REST API, poll job status, render charts/exports | Never calls Qiskit directly; never trusts client-side validation alone (server re-validates everything) |
| **Backend (API process)** | FastAPI + Pydantic + SQLAlchemy | Authenticate requests, validate input, read/write PostgreSQL, enqueue jobs, serve the public backend/algorithm catalog | Never executes a quantum circuit synchronously in a request handler |
| **Worker process** | Python (RQ consumer) | Dequeue jobs, re-validate, invoke the Quantum Execution Engine, persist results, manage job status transitions | Never accepts direct user input — only ever acts on a `job_id` already created by the API |
| **Quantum Execution Engine** | Qiskit + Qiskit Aer | Build circuits from validated JSON, transpile against a coupling map, run on the selected simulator backend, compute resource/noise diagnostics | Never talks to the database or HTTP layer directly — it is a pure function of (circuit, backend_type, shots, noise_config) → `ExecutionResult` |
| **PostgreSQL** | Postgres 16 | System of record: users, jobs, results, backends, experiments, experiment runs | Never holds unbounded statevector blobs (size-limited, see DATABASE_DESIGN.md) |
| **Redis** | Redis 7 | Job queue transport for RQ; rate-limit counters | Never stores anything that must survive a flush — it is a queue/cache, not a database |
| **Docker / Compose** | Docker Compose v2 | Reproducible multi-service deployment, health-checked startup ordering | Not responsible for production-grade orchestration (no auto-scaling, no rolling deploys) — that is explicitly out of scope for this prototype |

## 2. High-Level Architecture

```mermaid
graph TB
    User["User (browser)"]
    FE["Frontend<br/>React + TS + Vite + Tailwind"]
    API["Backend API<br/>FastAPI"]
    PG[("PostgreSQL")]
    RD[("Redis")]
    WK["Worker<br/>RQ consumer"]
    QE["Quantum Execution Engine<br/>Qiskit + Qiskit Aer"]

    User -->|HTTPS| FE
    FE -->|REST + JWT| API
    API -->|read/write| PG
    API -->|enqueue job| RD
    WK -->|dequeue job| RD
    WK -->|read/write| PG
    WK -->|invoke| QE
```

## 3. Component Architecture

```mermaid
graph LR
    subgraph Backend[FastAPI Backend]
        AUTH[auth router]
        BER[backends router]
        CIR[circuits router]
        JOB[jobs router]
        EXP[experiments router]
        ALG[algorithms router]
        DASH[dashboard router]
        SVC[services layer<br/>auth/job/circuit/backend/experiment]
        AUTH --> SVC
        BER --> SVC
        CIR --> SVC
        JOB --> SVC
        EXP --> SVC
        ALG --> SVC
        DASH --> SVC
    end

    subgraph Engine[Quantum Engine]
        CB[circuit_builder.py]
        NM[noise_models.py]
        EN[engine.py]
        AN[analysis.py]
        ALGLIB[algorithms/library.py]
        CB --> EN
        NM --> EN
    end

    SVC -->|validate + build| CB
    SVC -->|analyze/transpile| AN
    SVC -->|load algorithm| ALGLIB
    SVC -->|enqueue| Q[(RQ Queue)]
    Q --> W[Worker: tasks.py]
    W -->|execute| EN
    W -->|persist| DB[(PostgreSQL)]
    SVC -->|read/write| DB
```

## 4. Quantum Job Execution Sequence

```mermaid
sequenceDiagram
    participant U as User
    participant FE as Frontend
    participant API as Backend API
    participant DB as PostgreSQL
    participant Q as Redis Queue
    participant W as Worker
    participant QE as Quantum Engine

    U->>FE: Click "Execute circuit"
    FE->>API: POST /api/v1/jobs {circuit, backend_id, shots}
    API->>API: validate circuit JSON + qubit/shot limits
    API->>DB: INSERT quantum_jobs (status=QUEUED)
    API->>Q: enqueue(execute_quantum_job, job_id)
    API-->>FE: 201 {job_id, status: QUEUED}
    FE->>API: GET /api/v1/jobs/{id} (poll every 1.5s)

    Q->>W: deliver job
    W->>DB: UPDATE status=VALIDATING
    W->>W: rebuild circuit from JSON
    W->>DB: UPDATE status=RUNNING, started_at=now()
    W->>QE: execute_circuit(circuit, backend_type, shots, noise_config)
    QE-->>W: ExecutionResult (counts/probabilities/statevector, timings)
    W->>DB: INSERT quantum_results
    W->>DB: UPDATE status=COMPLETED, completed_at, execution_time

    FE->>API: GET /api/v1/jobs/{id} (status now COMPLETED)
    FE->>API: GET /api/v1/jobs/{id}/results
    API->>DB: SELECT quantum_results WHERE job_id=...
    API-->>FE: 200 {measurement_counts, probabilities, ...}
    FE-->>U: Render histogram + metadata
```

## 5. Circuit Submission (Validation) Sequence

```mermaid
sequenceDiagram
    participant FE as Frontend
    participant API as Backend API
    participant CB as circuit_builder.py

    FE->>API: POST /api/v1/circuits/validate {circuit}
    API->>CB: validate_circuit_json(circuit)
    alt circuit is structurally valid
        CB-->>API: no exception
        API-->>FE: 200 {valid: true, error: null}
    else circuit has an error (bad qubit index, unknown gate, wrong params)
        CB-->>API: raises CircuitValidationError(message)
        API-->>FE: 200 {valid: false, error: message}
    end
```

## 6. Deployment Architecture

```mermaid
graph TB
    subgraph Host["Docker host"]
        subgraph net["quantumcloud network"]
            FEC["frontend container<br/>nginx :80 -> host :5173"]
            APIC["backend container<br/>uvicorn :8000 -> host :8000"]
            WKC["worker container<br/>RQ worker (no exposed port)"]
            PGC["postgres container<br/>:5432"]
            RDC["redis container<br/>:6379"]
        end
        VOL[("postgres_data volume")]
        PGC --- VOL
    end

    FEC -->|REST| APIC
    APIC -->|SQL| PGC
    APIC -->|enqueue| RDC
    WKC -->|dequeue| RDC
    WKC -->|SQL| PGC

    APIC -.depends_on: healthy.-> PGC
    APIC -.depends_on: healthy.-> RDC
    WKC -.depends_on: healthy.-> PGC
    WKC -.depends_on: healthy.-> RDC
```

- Each service has a Docker `HEALTHCHECK` (backend: `curl /health`;
  frontend: `wget` against nginx; postgres: `pg_isready`; redis:
  `redis-cli ping`), and `depends_on: condition: service_healthy`
  ensures the backend/worker never start against a not-yet-ready
  database or queue.
- `docker-compose.dev.yml` overrides `backend`/`frontend` with
  hot-reload (`uvicorn --reload`, Vite dev server) and bind-mounts the
  source directories — the production compose file builds static,
  immutable images instead.

## 7. Communication Summary

- **Frontend ↔ Backend:** synchronous REST over HTTPS/HTTP, JWT bearer
  auth, JSON bodies.
- **Backend ↔ Queue:** fire-and-forget enqueue; the API never waits on
  a queued job.
- **Queue ↔ Worker:** pull-based (RQ workers poll/block on Redis); this
  means adding more worker replicas increases throughput without any
  backend change.
- **Worker ↔ Quantum Engine:** direct in-process function call — the
  engine is a library, not a separate service, because simulation
  state (a `QuantumCircuit` object) is not worth serializing across a
  network boundary for this scale.
- **Backend/Worker ↔ Database:** standard SQLAlchemy ORM sessions, one
  per request/job, closed deterministically (`finally: db.close()`).

## 8. Future Hardware Integration (design, not implementation)

`app/quantum/engine.py`'s `BACKEND_REGISTRY` dict and `execute_circuit`
dispatch are the intended seam: a fifth backend type (e.g.
`ibm_quantum`) would add an entry to `BACKEND_REGISTRY` and a new
branch in `execute_circuit` that submits to that provider's SDK and
polls for completion, returning the same `ExecutionResult` shape. No
other layer (API, job service, database schema, frontend) needs to
change, because they all depend only on `ExecutionResult`, not on how
it was produced. The main new work would be: provider credential
management (a new secret, not a new architecture concept), and
handling the fact that a real-hardware job may take minutes-to-hours
rather than seconds — which the existing async job model already
accommodates without redesign.

## 9. Verification Status of This Architecture

| Claim | Verified how |
|---|---|
| API never blocks on execution | Code review (enqueue, not synchronous call) + local behavior with a synchronous fakeredis queue still returning promptly for small circuits |
| Worker/engine separation | Code review — `app/api/*` never imports `app/quantum/engine` |
| Full Docker Compose stack boots together | **Not verified** — no Docker on this development machine (see PRD §12, Release 1 exit condition) |
| Health checks correctly gate startup order | **Not verified** — same reason |
| Horizontal worker scaling | **Not verified empirically** — architecturally sound (RQ workers are independent consumers of the same queue) but no multi-worker load test was run |
