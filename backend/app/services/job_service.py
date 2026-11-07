"""Job creation, listing, retrieval and cancellation — the API-facing
half of the job lifecycle (the worker-facing half is app/workers/tasks.py).
"""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import JobStatus, QuantumBackend, QuantumJob, QuantumResult, User
from app.quantum.circuit_builder import CircuitValidationError, validate_circuit_json
from app.workers.queue import get_queue
from app.workers.tasks import execute_quantum_job


def create_job(db: Session, user: User, circuit_config: dict, backend_id: str, shots: int, noise_config: dict | None) -> QuantumJob:
    try:
        validate_circuit_json(circuit_config)
    except CircuitValidationError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e))

    backend = db.get(QuantumBackend, backend_id)
    if backend is None or not backend.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Backend '{backend_id}' not found or inactive")

    num_qubits = circuit_config["num_qubits"]
    limit = settings.max_qubits_statevector if backend.backend_type == "statevector" else settings.max_qubits_shots
    if num_qubits > limit:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"{num_qubits} qubits exceeds the limit of {limit} for backend type '{backend.backend_type}'",
        )
    if shots > settings.max_shots:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"shots={shots} exceeds the limit of {settings.max_shots}")

    job = QuantumJob(
        user_id=user.id,
        backend_id=backend.id,
        circuit_config=circuit_config,
        shots=shots,
        noise_config=noise_config,
        status=JobStatus.QUEUED,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    get_queue().enqueue(
        execute_quantum_job,
        job.id,
        job_timeout=settings.job_execution_timeout_seconds,
    )
    # With a synchronous (fakeredis) queue, execute_quantum_job has already
    # run and committed via its own DB session by the time enqueue()
    # returns; refresh so the response reflects the real final state
    # rather than the pre-execution QUEUED snapshot held in this session.
    db.refresh(job)
    return job


def list_jobs(db: Session, user: User, status_filter: str | None = None, backend_id: str | None = None) -> list[QuantumJob]:
    query = db.query(QuantumJob).filter(QuantumJob.user_id == user.id)
    if status_filter:
        query = query.filter(QuantumJob.status == status_filter)
    if backend_id:
        query = query.filter(QuantumJob.backend_id == backend_id)
    return query.order_by(QuantumJob.submitted_at.desc()).all()


def get_job(db: Session, user: User, job_id: str) -> QuantumJob:
    job = db.get(QuantumJob, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    if job.user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have access to this job")
    return job


def get_job_result(db: Session, user: User, job_id: str) -> QuantumResult:
    job = get_job(db, user, job_id)
    if job.result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job has no results yet")
    return job.result


def cancel_job(db: Session, user: User, job_id: str) -> QuantumJob:
    job = get_job(db, user, job_id)
    if job.status not in (JobStatus.QUEUED, JobStatus.VALIDATING):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Job is '{job.status.value}' and can no longer be cancelled "
            "(cancellation is only guaranteed before execution starts)",
        )
    job.status = JobStatus.CANCELLED
    db.commit()
    return job
