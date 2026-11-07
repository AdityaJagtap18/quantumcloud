def test_validate_good_circuit(client, auth_headers):
    circuit = {"num_qubits": 2, "num_clbits": 2, "operations": [
        {"gate": "h", "qubits": [0]}, {"gate": "cx", "qubits": [0, 1]},
        {"gate": "measure", "qubits": [0], "clbits": [0]}, {"gate": "measure", "qubits": [1], "clbits": [1]},
    ]}
    r = client.post("/api/circuits/validate", headers=auth_headers, json={"circuit": circuit})
    assert r.status_code == 200
    assert r.json() == {"valid": True, "error": None}


def test_validate_bad_circuit(client, auth_headers):
    circuit = {"num_qubits": 2, "num_clbits": 1, "operations": [{"gate": "nonsense", "qubits": [0]}]}
    r = client.post("/api/circuits/validate", headers=auth_headers, json={"circuit": circuit})
    assert r.status_code == 200
    body = r.json()
    assert body["valid"] is False
    assert body["error"] is not None


def test_transpile_endpoint_reports_overhead(client, auth_headers):
    circuit = {"num_qubits": 3, "num_clbits": 3, "operations": [
        {"gate": "h", "qubits": [0]}, {"gate": "cx", "qubits": [0, 1]}, {"gate": "cx", "qubits": [1, 2]},
        {"gate": "measure", "qubits": [0], "clbits": [0]},
        {"gate": "measure", "qubits": [1], "clbits": [1]},
        {"gate": "measure", "qubits": [2], "clbits": [2]},
    ]}
    r = client.post("/api/circuits/transpile", headers=auth_headers, json={"circuit": circuit, "topology": "linear"})
    assert r.status_code == 200
    body = r.json()
    assert "transpiled_depth" in body
    assert "swap_gate_overhead" in body


def test_list_algorithms_public():
    pass  # covered via client fixture below in list_algorithms_returns_seven


def test_list_algorithms_returns_all(client):
    r = client.get("/api/algorithms")
    assert r.status_code == 200
    ids = {a["id"] for a in r.json()}
    assert {"bell_state", "ghz_state", "quantum_teleportation", "deutsch_jozsa",
            "bernstein_vazirani", "grover_search", "qft"} <= ids


def test_load_bernstein_vazirani_and_run_recovers_secret(client, auth_headers):
    load_resp = client.post("/api/algorithms/bernstein_vazirani/load", headers=auth_headers)
    circuit = load_resp.json()["circuit"]

    backends = client.get("/api/backends", headers=auth_headers).json()
    ideal = next(b for b in backends if b["backend_type"] == "ideal_qasm")

    job_resp = client.post("/api/jobs", headers=auth_headers, json={
        "circuit": circuit, "backend_id": ideal["id"], "shots": 1000,
    })
    job = job_resp.json()
    results = client.get(f"/api/jobs/{job['id']}/results", headers=auth_headers).json()
    counts = results["measurement_counts"]
    # Bernstein-Vazirani deterministically recovers the secret "101" in every shot.
    assert counts == {"101": 1000}


def test_job_cancellation_before_execution():
    """Cancellation is only meaningful before a job starts executing. The
    fakeredis queue used elsewhere runs jobs synchronously on enqueue, so
    to test cancellation for real we create a QUEUED job directly at the
    DB/service layer (bypassing the queue) and cancel it before any
    worker would have touched it."""
    from app.db.session import SessionLocal
    from app.models.models import JobStatus, QuantumBackend, QuantumJob, User
    from app.services.job_service import cancel_job

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "tester@example.com").first()
        if user is None:
            from app.core.security import hash_password
            user = User(email="cancel_test_user@example.com", password_hash=hash_password("password123"))
            db.add(user)
            db.commit()
            db.refresh(user)

        backend = db.query(QuantumBackend).filter(QuantumBackend.backend_type == "ideal_qasm").first()
        job = QuantumJob(
            user_id=user.id, backend_id=backend.id,
            circuit_config={"num_qubits": 1, "num_clbits": 1, "operations": []},
            shots=100, status=JobStatus.QUEUED,
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        cancelled = cancel_job(db, user, job.id)
        assert cancelled.status == JobStatus.CANCELLED

        # A job that's already terminal cannot be cancelled again.
        from fastapi import HTTPException
        try:
            cancel_job(db, user, job.id)
            assert False, "expected HTTPException on double-cancel"
        except HTTPException as e:
            assert e.status_code == 409
    finally:
        db.close()
