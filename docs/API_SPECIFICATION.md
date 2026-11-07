# API_SPECIFICATION.md — QuantumCloud REST API Contract

**Convention:** all endpoints are specified under `/api/v1/...` per
REST versioning best practice.

> **Implementation note:** the current prototype implements every
> endpoint below under an unversioned `/api/...` prefix (e.g.
> `/api/jobs`, not `/api/v1/jobs`). This is a deliberate flag, not an
> oversight: adding version-prefix routing is a mechanical change
> (one `APIRouter(prefix=...)` edit per router) tracked as a Release 2
> follow-up item in `ROADMAP.md`, and every endpoint's *behavior*
> described below has been implemented and tested against the
> unversioned path. All examples in this document use `/api/v1/` as
> the target convention.

Authentication: Bearer JWT (`Authorization: Bearer <token>`), obtained
from `/api/v1/auth/login`. Endpoints marked **Public** require no
token.

---

## Authentication

### `POST /api/v1/auth/register`
- **Purpose:** Create a new user account.
- **Auth:** Public
- **Request:**
  ```json
  { "email": "demo@quantumcloud.dev", "password": "password123" }
  ```
- **Validation:** `email` must be a valid email address; `password`
  minimum 8 characters.
- **Response `201`:**
  ```json
  { "id": "uuid", "email": "demo@quantumcloud.dev", "created_at": "2026-10-31T09:00:00Z" }
  ```
- **Errors:** `409` if the email is already registered; `422` on
  validation failure.

### `POST /api/v1/auth/login`
- **Purpose:** Authenticate and obtain a JWT.
- **Auth:** Public
- **Request:** `{ "email": "...", "password": "..." }`
- **Response `200`:** `{ "access_token": "<jwt>", "token_type": "bearer" }`
- **Errors:** `401` on invalid credentials.

---

## Backends

### `GET /api/v1/backends`
- **Purpose:** List all active simulation backends.
- **Auth:** Public
- **Response `200`:**
  ```json
  [
    {
      "id": "uuid", "name": "Ideal QASM Simulator", "backend_type": "ideal_qasm",
      "description": "Noiseless shot-based simulation returning measurement counts.",
      "requires_measurements": true
    }
  ]
  ```

### `GET /api/v1/backends/{backend_id}`
- **Purpose:** Get one backend's detail.
- **Auth:** Public
- **Errors:** `404` if not found.

---

## Circuits

### `POST /api/v1/circuits/validate`
- **Purpose:** Check a circuit's structural validity without executing it.
- **Auth:** Required
- **Request:** `{ "circuit": { "num_qubits": 2, "num_clbits": 2, "operations": [...] } }`
- **Response `200`:** `{ "valid": true, "error": null }` or
  `{ "valid": false, "error": "operations[0] uses unknown gate 'xx'..." }`
- **Validation rules:** qubit/clbit counts positive/non-negative;
  every `operations[i].qubits` index within `[0, num_qubits)`; gate
  name in the supported set; parameter count matches the gate;
  `measure` requires matching-length `clbits`; an optional
  `condition: {clbit, equals}` must reference a valid clbit.

### `POST /api/v1/circuits/analyze`
- **Purpose:** Pre- and post-transpilation resource report.
- **Auth:** Required
- **Request:** `{ "circuit": {...}, "topology": "linear" }`
  (topology ∈ `fully_connected | linear | ring | heavy_hex_like`)
- **Response `200`:**
  ```json
  {
    "logical": { "num_qubits": 3, "num_clbits": 3, "total_gate_count": 3,
                 "single_qubit_gate_count": 1, "two_qubit_gate_count": 2,
                 "depth": 4, "num_measurements": 3, "width": 6,
                 "gate_distribution": { "h": 1, "cx": 2, "measure": 3 } },
    "transpiled": { "topology": "linear", "transpiled_depth": 6,
                     "transpiled_gate_count": 5,
                     "native_gate_distribution": { "rz": 2, "sx": 1, "cx": 2, "measure": 3 },
                     "swap_gate_overhead": 0, "transpile_time_seconds": 0.0066,
                     "resource_overhead_ratio": 1.67, "depth_overhead_ratio": 1.5 }
  }
  ```
- **Errors:** `422` if the circuit is invalid.

### `POST /api/v1/circuits/transpile`
- **Purpose:** Transpiled-only report (subset of `/analyze`'s `transpiled` block), with an `optimization_level` (0–3) parameter.
- **Auth:** Required

---

## Jobs

### `POST /api/v1/jobs`
- **Purpose:** Submit a circuit for asynchronous execution.
- **Auth:** Required
- **Request:**
  ```json
  {
    "circuit": { "num_qubits": 2, "num_clbits": 2, "operations": [
      {"gate": "h", "qubits": [0]}, {"gate": "cx", "qubits": [0, 1]},
      {"gate": "measure", "qubits": [0], "clbits": [0]},
      {"gate": "measure", "qubits": [1], "clbits": [1]}
    ]},
    "backend_id": "uuid-of-ideal_qasm",
    "shots": 2000,
    "noise_config": null
  }
  ```
- **Response `201`:** the created `QuantumJob` (see `DATABASE_DESIGN.md`
  for the full field list), `status: "QUEUED"`.
- **Validation rules:** circuit must pass `/validate`'s rules;
  `num_qubits` must not exceed the backend-type-specific qubit limit
  (20 for `statevector`, 30 otherwise, by default); `shots` ≤ 100000.
- **Errors:** `422` (invalid circuit or over limit), `404` (unknown/
  inactive backend).

### `GET /api/v1/jobs`
- **Purpose:** List the authenticated user's own jobs.
- **Auth:** Required
- **Query params:** `status` (optional, one of the 6 job statuses),
  `backend_id` (optional).
- **Response `200`:** array of `QuantumJob`, newest first.

### `GET /api/v1/jobs/{job_id}`
- **Purpose:** Get one job's current status/metadata.
- **Auth:** Required (must be the owning user)
- **Errors:** `404` unknown job; `403` job belongs to another user.

### `POST /api/v1/jobs/{job_id}/cancel`
- **Purpose:** Cancel a job before it starts running.
- **Auth:** Required (owner only)
- **Response `200`:** the job with `status: "CANCELLED"`.
- **Errors:** `409` if the job is no longer `QUEUED`/`VALIDATING`
  (already running or terminal).

### `GET /api/v1/jobs/{job_id}/results`
- **Purpose:** Retrieve a completed job's measurement/statevector result.
- **Auth:** Required (owner only)
- **Response `200`:**
  ```json
  {
    "job_id": "uuid",
    "measurement_counts": { "00": 1013, "11": 987 },
    "probabilities": { "00": 0.5065, "11": 0.4935 },
    "statevector": null,
    "execution_metadata": {
      "backend_name": "Ideal QASM Simulator", "shots": 2000,
      "execution_time_seconds": 0.0047, "transpile_time_seconds": 0.0012,
      "noisy": false, "num_qubits": 2
    }
  }
  ```
- **Errors:** `404` if the job has no results yet (not completed).

---

## Experiments (Noise Studio)

### `POST /api/v1/experiments`
- **Purpose:** Run a noise sweep (synchronously, since each level is
  typically fast) and persist every run.
- **Auth:** Required
- **Request:**
  ```json
  {
    "experiment_name": "bell-noise-sweep",
    "circuit": { "...": "..." },
    "backend_id": "uuid-of-ideal_qasm",
    "shots": 2000,
    "noise_levels": [0.0, 0.01, 0.03, 0.05, 0.10]
  }
  ```
- **Response `201`:** the created `Experiment` record.

### `GET /api/v1/experiments`
- **Purpose:** List the user's experiments.
- **Auth:** Required

### `GET /api/v1/experiments/{experiment_id}`
- **Purpose:** Get an experiment and all its runs (per noise level).
- **Auth:** Required (owner only)
- **Response `200`:**
  ```json
  {
    "experiment": { "id": "uuid", "experiment_name": "bell-noise-sweep", "...": "..." },
    "runs": [
      { "id": "uuid", "noise_level": 0.0, "job_id": null,
        "metrics": { "fidelity_proxy": 1.0, "observable_error": 0.0,
                     "measurement_counts": {"00": 2012, "11": 1988}, "...": "..." } }
    ]
  }
  ```

### `POST /api/v1/experiments/{experiment_id}/run`
- **Purpose:** Re-execute an existing experiment's stored configuration (useful for reproducibility checks).
- **Auth:** Required (owner only)
- **Response `201`:** a new `Experiment` record (named `"<original> (rerun)"`).

---

## Algorithms

### `GET /api/v1/algorithms`
- **Purpose:** List the prebuilt algorithm catalog.
- **Auth:** Public
- **Response `200`:** array of `{ id, name, description, math_intuition, expected_distribution }`.

### `GET /api/v1/algorithms/{algorithm_id}`
- **Auth:** Public
- **Errors:** `404` unknown algorithm.

### `POST /api/v1/algorithms/{algorithm_id}/load`
- **Purpose:** Get the algorithm's circuit in this project's JSON format, ready to submit as a job.
- **Auth:** Required
- **Response `200`:** `{ "circuit": { "num_qubits": ..., "num_clbits": ..., "operations": [...] } }`

---

## Dashboard

### `GET /api/v1/dashboard/stats`
- **Purpose:** Aggregate job statistics for the authenticated user.
- **Auth:** Required
- **Response `200`:**
  ```json
  {
    "total_jobs": 12, "completed_jobs": 10, "failed_jobs": 1,
    "running_jobs": 0, "queued_jobs": 1,
    "average_execution_time_seconds": 0.0231,
    "recent_jobs": [ { "id": "uuid", "status": "COMPLETED", "backend_id": "uuid",
                        "submitted_at": "...", "execution_time": 0.0047 } ]
  }
  ```

---

## Health

### `GET /health`
- **Purpose:** Liveness check (used by the Docker `HEALTHCHECK`).
- **Auth:** Public
- **Response `200`:** `{ "status": "ok", "app": "QuantumCloud" }`

---

## Cross-cutting error format

All validation/auth errors follow FastAPI's default shape:
```json
{ "detail": "human-readable message" }
```
or, for Pydantic body validation (`422`), FastAPI's standard
`{"detail": [{"loc": [...], "msg": "...", "type": "..."}]}` array.
No endpoint returns a stack trace or internal exception text to the
client (unhandled exceptions are caught by FastAPI's default handler
and return a generic `500` — see `TESTING_STRATEGY.md` for the gap
this leaves: no automated test currently asserts that an unexpected
engine exception never leaks internal detail to an API response).
