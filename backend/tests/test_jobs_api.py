"""Job submission, lifecycle, result retrieval and ownership tests.
REDIS_URL=fakeredis:// makes the queue synchronous, so by the time
POST /api/jobs returns, the job has already run through the real
quantum engine — no mocked execution."""

BELL_CIRCUIT = {
    "num_qubits": 2, "num_clbits": 2,
    "operations": [
        {"gate": "h", "qubits": [0]},
        {"gate": "cx", "qubits": [0, 1]},
        {"gate": "measure", "qubits": [0], "clbits": [0]},
        {"gate": "measure", "qubits": [1], "clbits": [1]},
    ],
}


def _ideal_backend_id(client, auth_headers):
    backends = client.get("/api/backends", headers=auth_headers).json()
    return next(b["id"] for b in backends if b["backend_type"] == "ideal_qasm")


def test_submit_job_and_retrieve_results(client, auth_headers):
    backend_id = _ideal_backend_id(client, auth_headers)
    r = client.post("/api/jobs", headers=auth_headers, json={
        "circuit": BELL_CIRCUIT, "backend_id": backend_id, "shots": 2000,
    })
    assert r.status_code == 201
    job = r.json()
    assert job["status"] == "COMPLETED"  # synchronous fakeredis queue

    results = client.get(f"/api/jobs/{job['id']}/results", headers=auth_headers)
    assert results.status_code == 200
    counts = results.json()["measurement_counts"]
    assert sum(counts.values()) == 2000
    assert set(counts.keys()) <= {"00", "11"}


def test_invalid_circuit_rejected(client, auth_headers):
    backend_id = _ideal_backend_id(client, auth_headers)
    bad_circuit = {"num_qubits": 2, "num_clbits": 1, "operations": [{"gate": "not_a_gate", "qubits": [0]}]}
    r = client.post("/api/jobs", headers=auth_headers, json={
        "circuit": bad_circuit, "backend_id": backend_id, "shots": 100,
    })
    assert r.status_code == 422


def test_job_listing_filters_by_status(client, auth_headers):
    backend_id = _ideal_backend_id(client, auth_headers)
    client.post("/api/jobs", headers=auth_headers, json={
        "circuit": BELL_CIRCUIT, "backend_id": backend_id, "shots": 500,
    })
    r = client.get("/api/jobs?status=COMPLETED", headers=auth_headers)
    assert r.status_code == 200
    assert all(j["status"] == "COMPLETED" for j in r.json())


def test_unauthorized_job_access_rejected(client, auth_headers):
    backend_id = _ideal_backend_id(client, auth_headers)
    r = client.post("/api/jobs", headers=auth_headers, json={
        "circuit": BELL_CIRCUIT, "backend_id": backend_id, "shots": 500,
    })
    job_id = r.json()["id"]

    client.post("/api/auth/register", json={"email": "other_user@example.com", "password": "password123"})
    other_token = client.post("/api/auth/login", json={"email": "other_user@example.com", "password": "password123"}).json()["access_token"]
    other_headers = {"Authorization": f"Bearer {other_token}"}

    r2 = client.get(f"/api/jobs/{job_id}", headers=other_headers)
    assert r2.status_code == 403


def test_qubit_limit_enforced(client, auth_headers):
    backend_id = _ideal_backend_id(client, auth_headers)
    huge_circuit = {"num_qubits": 999, "num_clbits": 1, "operations": [
        {"gate": "h", "qubits": [0]}, {"gate": "measure", "qubits": [0], "clbits": [0]}
    ]}
    r = client.post("/api/jobs", headers=auth_headers, json={
        "circuit": huge_circuit, "backend_id": backend_id, "shots": 100,
    })
    assert r.status_code == 422


def test_job_not_found_returns_404(client, auth_headers):
    r = client.get("/api/jobs/does-not-exist", headers=auth_headers)
    assert r.status_code == 404
