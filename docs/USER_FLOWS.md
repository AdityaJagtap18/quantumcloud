# USER_FLOWS.md — Journeys, Sequence Diagrams, and UI/UX Requirements

## Journey 1: Execute a Bell State Circuit

**Starting conditions:** User has a registered account and is logged in.

**User actions:**
1. Navigate to Circuit Lab.
2. (Default circuit is already a Bell state — H(q0), CX(q0,q1),
   measure both — or the user builds it via the gate toolbar.)
3. Select backend "Ideal QASM Simulator."
4. Set shots (default 1024).
5. Click "Execute circuit."

**System responses:**
1. Frontend calls `POST /api/v1/circuits/validate` implicitly is not
   required here since `/jobs` validates server-side; frontend calls
   `POST /api/v1/jobs`.
2. Backend validates, creates a `QUEUED` job, enqueues it.
3. Frontend navigates to the Job Details page and polls
   `GET /api/v1/jobs/{id}` every 1.5s.
4. Worker executes; job reaches `COMPLETED`.
5. Frontend fetches `GET /api/v1/jobs/{id}/results` and renders the
   histogram.

**Success condition:** histogram shows only `00`/`11` bitstrings,
roughly evenly split.

**Failure conditions:** backend unreachable (network error shown as
`ErrorState`); circuit somehow invalid (shouldn't happen with the
default circuit — would show `422` detail); job reaches `FAILED` (UI
shows `error_message` in an `ErrorState` on the Job Details page).

**Relevant API calls:** `POST /api/v1/jobs`, `GET /api/v1/jobs/{id}`
(repeated), `GET /api/v1/jobs/{id}/results`.

**Verified:** this exact journey was executed live in a browser during
development — 514/1024 "11", 510/1024 "00" at 1024 shots.

---

## Journey 2: Execute a Noisy Circuit and Compare

**Starting conditions:** User is logged in, on the Noise Studio page.

**User actions:**
1. Build or keep the default Bell circuit.
2. Enter noise levels (e.g., `0.0, 0.01, 0.03, 0.05, 0.10`).
3. Set shots per level.
4. Click "Run noise sweep."

**System responses:**
1. Frontend calls `POST /api/v1/experiments` with the circuit, an
   ideal backend id, shots, and noise levels.
2. Backend (`experiment_service.run_noise_sweep`): runs one 4000-shot
   ideal baseline, then one execution per noise level with a scaled
   custom noise config, computing total-variation-distance-based
   `observable_error` and `fidelity_proxy` against the baseline for
   each.
3. Frontend fetches `GET /api/v1/experiments/{id}` for the full run
   list and renders a line chart of fidelity/error vs. noise level.

**Success condition:** fidelity_proxy trends downward (or flat within
statistical noise) as noise level increases; chart renders without error.

**Failure condition:** invalid circuit (no measurements) → `422` with
a message that noise-sweep circuits must include measurements.

**Relevant API calls:** `GET /api/v1/backends`, `POST /api/v1/experiments`,
`GET /api/v1/experiments/{id}`.

**Verified:** live run showed fidelity dropping from 1.0 toward ~0.68
across the default noise levels.

---

## Journey 3: Inspect Circuit Resources Before/After Transpilation

**Starting conditions:** User is on the Circuit Lab with a multi-qubit
circuit built (e.g., GHZ(3)).

**User actions:**
1. Select a hardware topology (e.g., "Linear chain") in the Resource
   Analysis panel.
2. Click "Analyze circuit."

**System responses:**
1. Frontend calls `POST /api/v1/circuits/analyze` with the circuit and
   topology.
2. Backend computes logical metrics (depth, gate counts) directly from
   the circuit, then transpiles against the chosen coupling map and
   computes the post-transpilation metrics, returning both in one
   response.
3. Frontend renders a 2×3 metric grid: logical depth vs. transpiled
   depth, logical gates vs. transpiled gates, SWAP overhead, overhead
   ratio.

**Success condition:** both logical and transpiled numbers are shown,
distinguishable from each other (never merged into one number).

**Failure condition:** invalid circuit → `422`.

**Relevant API calls:** `POST /api/v1/circuits/analyze`.

**Verified:** live run on the default Bell circuit against
"Fully connected" showed logical depth 3 / transpiled depth 3, 2
logical gates / 2 transpiled gates, 0 SWAP overhead, 1.00 ratio — i.e.
no overhead on a fully-connected topology, as expected for a 2-qubit
circuit.

---

## Journey 4: Execute a Prebuilt Algorithm

**Starting conditions:** User is logged in, on the Algorithm Library page.

**User actions:**
1. Browse the 7 algorithm cards.
2. Click "Load into Circuit Lab" on, e.g., Bernstein-Vazirani.
3. (Redirected to Circuit Lab with the circuit pre-populated.)
4. Select the ideal backend and click "Execute circuit."

**System responses:**
1. Frontend calls `POST /api/v1/algorithms/bernstein_vazirani/load`,
   receives the circuit JSON, and navigates to `/circuit-lab` with it
   in route state.
2. Circuit Lab renders the loaded circuit in the wire editor
   (read/editable, same as any user-built circuit).
3. Submission proceeds exactly as Journey 1.

**Success condition:** for Bernstein-Vazirani with secret `"101"`, the
histogram shows `101` as the *only* outcome (probability 1, by
construction of the algorithm) — a deterministic, not statistical,
check.

**Failure condition:** none expected for a correctly-implemented
algorithm; if the histogram shows any other bitstring, that indicates
an implementation bug in `app/algorithms/library.py`, not a user error.

**Relevant API calls:** `GET /api/v1/algorithms`,
`POST /api/v1/algorithms/{id}/load`, then Journey 1's calls.

**Verified:** `test_load_bernstein_vazirani_and_run_recovers_secret`
asserts exactly `{"101": 1000}` for 1000 shots — a passing automated
test, not just a manual spot-check.

---

## UI/UX Requirements — Screen Specifications

### 1. Dashboard
- **Purpose:** At-a-glance account health.
- **Components:** 5 stat cards (total/completed/running/queued/failed
  jobs), average execution time card, recent-jobs table (10 rows).
- **Interactions:** click a recent job to open its Job Details.
- **Backend data:** `GET /api/v1/dashboard/stats`.
- **Loading:** spinner (`LoadingState`) until stats resolve.
- **Empty:** "No jobs yet" with a hint to visit Circuit Lab, for a
  brand-new account.
- **Error:** `ErrorState` banner if the stats call fails.

### 2. Quantum Circuit Lab
- **Purpose:** Build, analyze, and execute a circuit.
- **Components:** qubit/clbit steppers, gate/qubit/angle selectors,
  "Add gate"/"Clear circuit" buttons, wire visualization, backend
  selector + shots input + "Execute circuit," topology selector +
  "Analyze circuit" + metric grid.
- **Interactions:** click a placed gate to remove it; select a
  two-qubit gate to reveal a target-qubit selector; rotation gates
  reveal an angle input.
- **Backend data:** `GET /api/v1/backends`, `POST /api/v1/circuits/analyze`,
  `POST /api/v1/jobs`.
- **Loading:** buttons show "Analyzing..."/"Submitting..." text while
  their respective call is in flight.
- **Empty:** wire panel shows "No gates yet" prompt when
  `operations.length === 0`.
- **Error:** `ErrorState` banner below the editor on a failed
  analyze/submit call.

### 3. Backend Selection
- *(Implemented as a selector within Circuit Lab, not a standalone
  page — see PRD §4 Module C. A dedicated comparison screen is a
  Release 3 item; see `ROADMAP.md`.)*
- **Purpose:** Choose which simulator a job runs on, with its
  description visible so the user understands what they're selecting.
- **Backend data:** `GET /api/v1/backends`.

### 4. Job Explorer
- **Purpose:** Browse and filter job history.
- **Components:** status filter dropdown, backend filter dropdown,
  table (job id, backend, status, qubits, submitted, duration).
- **Interactions:** click a job id to open Job Details.
- **Backend data:** `GET /api/v1/jobs?status=&backend_id=`.
- **Loading:** `LoadingState` while the filtered list is fetched.
- **Empty:** "No jobs match these filters" with a hint.
- **Error:** `ErrorState` on fetch failure.

### 5. Job Details
- **Purpose:** Full detail + live status for one job.
- **Components:** status pill, cancel button (while cancellable),
  metadata cards (qubits/shots/submitted/execution time), histogram
  or statevector-probability chart, execution metadata JSON block,
  export buttons.
- **Interactions:** auto-polls while `QUEUED`/`VALIDATING`/`RUNNING`;
  "Cancel job" button only rendered in those states; export buttons
  download JSON/CSV client-side.
- **Backend data:** `GET /api/v1/jobs/{id}`, `GET /api/v1/jobs/{id}/results`,
  `POST /api/v1/jobs/{id}/cancel`.
- **Loading:** `LoadingState` with the current status text while
  non-terminal.
- **Empty:** N/A (a job always has at least its own metadata).
- **Error:** `ErrorState` showing `error_message` for a `FAILED` job.

### 6. Results Visualization
- *(Implemented as part of Job Details — histogram, probability chart,
  metadata block — rather than a separate route, since results are
  always viewed in the context of one job.)*

### 7. Noise Experimentation Studio
- **Purpose:** Run and visualize noise sweeps.
- **Components:** circuit editor (shared `CircuitEditor` component),
  noise-level input, shots input, "Run noise sweep" button, line chart
  (fidelity proxy + observable error vs. noise level).
- **Interactions:** editing the circuit before running a new sweep.
- **Backend data:** `GET /api/v1/backends`, `POST /api/v1/experiments`,
  `GET /api/v1/experiments/{id}`.
- **Loading:** button shows "Running sweep..."; chart area stays empty
  until results arrive.
- **Empty:** "No sweep run yet" prompt before the first run.
- **Error:** `ErrorState` on sweep failure.

### 8. Algorithm Library
- **Purpose:** Browse and load prebuilt algorithms.
- **Components:** one card per algorithm (name, description, math
  intuition, expected outcome if deterministic, "Load into Circuit
  Lab" button).
- **Backend data:** `GET /api/v1/algorithms`,
  `POST /api/v1/algorithms/{id}/load`.
- **Loading:** `LoadingState` while the catalog loads; button shows
  "Loading..." while fetching that specific algorithm's circuit.
- **Empty:** N/A (catalog is static/seeded, never empty).
- **Error:** `ErrorState` if the catalog or a load call fails.

### 9. User Settings
- *(Not yet implemented — see PRD FR-AUTH-005, Release 3. Current
  account management is limited to register/login/logout; there is no
  profile-editing or password-change screen yet.)*
- **Purpose (planned):** view email/creation date, change password,
  log out.
- **Backend data (planned):** `GET /api/v1/users/me` (not yet built).

---

## Cross-screen conventions

- Dark/light theme toggle lives in the sidebar and persists via
  `localStorage` + `prefers-color-scheme` fallback, applied through a
  `data-theme` attribute consumed by CSS custom properties — consistent
  across all 9 screens.
- All list/detail pages follow the same `LoadingState` /
  `EmptyState` / `ErrorState` component trio (`src/components/States.tsx`)
  so empty and error handling is visually consistent rather than
  bespoke per page.
