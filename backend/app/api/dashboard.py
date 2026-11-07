"""Aggregate statistics for the frontend Dashboard page. Every number
here is computed from real rows in quantum_jobs — nothing hardcoded.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import JobStatus, QuantumJob, User
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
def get_stats(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    base = db.query(QuantumJob).filter(QuantumJob.user_id == user.id)

    total = base.count()
    completed = base.filter(QuantumJob.status == JobStatus.COMPLETED).count()
    failed = base.filter(QuantumJob.status == JobStatus.FAILED).count()
    running = base.filter(QuantumJob.status == JobStatus.RUNNING).count()
    queued = base.filter(QuantumJob.status == JobStatus.QUEUED).count()

    avg_time = (
        db.query(func.avg(QuantumJob.execution_time))
        .filter(QuantumJob.user_id == user.id, QuantumJob.status == JobStatus.COMPLETED)
        .scalar()
    )

    recent = base.order_by(QuantumJob.submitted_at.desc()).limit(10).all()

    return {
        "total_jobs": total,
        "completed_jobs": completed,
        "failed_jobs": failed,
        "running_jobs": running,
        "queued_jobs": queued,
        "average_execution_time_seconds": float(avg_time) if avg_time is not None else None,
        "recent_jobs": [
            {
                "id": j.id,
                "status": j.status.value,
                "backend_id": j.backend_id,
                "submitted_at": j.submitted_at.isoformat(),
                "execution_time": j.execution_time,
            }
            for j in recent
        ],
    }
