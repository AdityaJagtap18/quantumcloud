"""The RQ job function: loads a QuantumJob by id, runs it through the
real quantum execution engine, and persists the result. This is the
only place a job transitions QUEUED -> VALIDATING -> RUNNING -> COMPLETED/FAILED.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from app.db.session import SessionLocal
from app.models.models import JobStatus, QuantumBackend, QuantumJob, QuantumResult
from app.quantum.circuit_builder import CircuitValidationError, build_circuit
from app.quantum.engine import QuantumExecutionError, execute_circuit

logger = logging.getLogger("quantumcloud.worker")

MAX_STATEVECTOR_JSON_QUBITS = 16  # 2^16 complex amplitudes is already a lot of JSON; cap storage


def execute_quantum_job(job_id: str) -> None:
    db = SessionLocal()
    try:
        job = db.get(QuantumJob, job_id)
        if job is None:
            logger.error(f"Job {job_id} not found; nothing to execute")
            return

        if job.status == JobStatus.CANCELLED:
            logger.info(f"Job {job_id} was cancelled before execution started")
            return

        job.status = JobStatus.VALIDATING
        db.commit()

        try:
            circuit = build_circuit(job.circuit_config)
        except CircuitValidationError as e:
            _fail_job(db, job, f"Circuit validation failed: {e}")
            return

        backend = db.get(QuantumBackend, job.backend_id)
        if backend is None:
            _fail_job(db, job, f"Backend {job.backend_id} not found")
            return

        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(timezone.utc)
        db.commit()

        start = time.perf_counter()
        try:
            result = execute_circuit(
                circuit,
                backend_type=backend.backend_type,
                shots=job.shots,
                noise_config=job.noise_config,
            )
        except QuantumExecutionError as e:
            _fail_job(db, job, str(e))
            return
        except Exception as e:  # noqa: BLE001 - genuinely unexpected engine failure
            logger.exception(f"Unexpected error executing job {job_id}")
            _fail_job(db, job, f"Unexpected execution error: {e}")
            return
        execution_time = time.perf_counter() - start

        statevector_payload = None
        if result.statevector is not None and circuit.num_qubits <= MAX_STATEVECTOR_JSON_QUBITS:
            statevector_payload = result.statevector

        db_result = QuantumResult(
            job_id=job.id,
            measurement_counts=result.measurement_counts,
            probabilities=result.probabilities,
            statevector=statevector_payload,
            execution_metadata={
                "backend_name": result.backend_name,
                "shots": result.shots,
                "execution_time_seconds": result.execution_time_seconds,
                "transpile_time_seconds": result.transpile_time_seconds,
                **result.metadata,
            },
        )
        db.add(db_result)

        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.now(timezone.utc)
        job.execution_time = execution_time
        db.commit()
        logger.info(f"Job {job_id} completed in {execution_time:.4f}s")

    finally:
        db.close()


def _fail_job(db, job: QuantumJob, message: str) -> None:
    job.status = JobStatus.FAILED
    job.error_message = message
    job.completed_at = datetime.now(timezone.utc)
    db.commit()
    logger.warning(f"Job {job.id} failed: {message}")
