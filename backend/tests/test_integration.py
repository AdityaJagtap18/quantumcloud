"""End-to-end integration test: register -> login -> load a prebuilt
algorithm -> analyze/transpile it -> submit as a job -> poll status ->
retrieve real measurement results from the API, exactly as a frontend
client would. No quantum execution is mocked anywhere in this path.
"""


def test_full_bell_state_lifecycle(client):
    # 1. Register and log in
    client.post("/api/auth/register", json={"email": "integration@example.com", "password": "password123"})
    token = client.post("/api/auth/login", json={"email": "integration@example.com", "password": "password123"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Load the Bell state algorithm
    load_resp = client.post("/api/algorithms/bell_state/load", headers=headers)
    assert load_resp.status_code == 200
    circuit = load_resp.json()["circuit"]
    assert circuit["num_qubits"] == 2

    # 3. Analyze circuit resources before execution
    analyze_resp = client.post("/api/circuits/analyze", headers=headers, json={"circuit": circuit, "topology": "linear"})
    assert analyze_resp.status_code == 200
    analysis = analyze_resp.json()
    assert analysis["logical"]["total_gate_count"] >= 2
    assert analysis["transpiled"]["transpiled_depth"] >= analysis["logical"]["depth"]

    # 4. Submit to the ideal simulator
    backends = client.get("/api/backends", headers=headers).json()
    ideal_backend = next(b for b in backends if b["backend_type"] == "ideal_qasm")

    job_resp = client.post("/api/jobs", headers=headers, json={
        "circuit": circuit, "backend_id": ideal_backend["id"], "shots": 3000,
    })
    assert job_resp.status_code == 201
    job = job_resp.json()
    assert job["status"] == "COMPLETED"
    assert job["execution_time"] is not None

    # 5. Poll job status (even though it's already done with the sync queue)
    status_resp = client.get(f"/api/jobs/{job['id']}", headers=headers)
    assert status_resp.json()["status"] == "COMPLETED"

    # 6. Retrieve and validate real measurement results
    results_resp = client.get(f"/api/jobs/{job['id']}/results", headers=headers)
    counts = results_resp.json()["measurement_counts"]
    assert sum(counts.values()) == 3000
    assert set(counts.keys()) <= {"00", "11"}

    # 7. Run the same circuit noisy, and compare via the Noise Studio endpoint
    experiment_resp = client.post("/api/experiments", headers=headers, json={
        "experiment_name": "bell_noise_sweep",
        "circuit": circuit,
        "backend_id": ideal_backend["id"],
        "shots": 2000,
        "noise_levels": [0.0, 0.05, 0.15],
    })
    assert experiment_resp.status_code == 201
    experiment = experiment_resp.json()

    detail_resp = client.get(f"/api/experiments/{experiment['id']}", headers=headers)
    runs = detail_resp.json()["runs"]
    assert len(runs) == 3
    fidelities = [r["metrics"]["fidelity_proxy"] for r in sorted(runs, key=lambda r: r["noise_level"])]
    # Fidelity proxy should generally decrease as noise increases (allow one inversion for statistical noise).
    assert fidelities[0] >= fidelities[-1] - 0.05
