from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import User
from app.schemas.schemas import JobCreateRequest, JobOut, JobResultOut
from app.services.auth_service import get_current_user
from app.services.job_service import cancel_job, create_job, get_job, get_job_result, list_jobs

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post("", response_model=JobOut, status_code=201)
def submit_job(payload: JobCreateRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = create_job(
        db, user,
        circuit_config=payload.circuit.model_dump(),
        backend_id=payload.backend_id,
        shots=payload.shots,
        noise_config=payload.noise_config,
    )
    return job


@router.get("", response_model=list[JobOut])
def get_jobs(
    status_filter: str | None = Query(None, alias="status"),
    backend_id: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_jobs(db, user, status_filter=status_filter, backend_id=backend_id)


@router.get("/{job_id}", response_model=JobOut)
def get_job_detail(job_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_job(db, user, job_id)


@router.post("/{job_id}/cancel", response_model=JobOut)
def cancel(job_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return cancel_job(db, user, job_id)


@router.get("/{job_id}/results", response_model=JobResultOut)
def get_results(job_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = get_job_result(db, user, job_id)
    return JobResultOut(
        job_id=result.job_id,
        measurement_counts=result.measurement_counts,
        probabilities=result.probabilities,
        statevector=result.statevector,
        execution_metadata=result.execution_metadata,
    )
