from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import Experiment, User
from app.schemas.schemas import ExperimentCreateRequest, ExperimentOut, ExperimentRunOut
from app.services.auth_service import get_current_user
from app.services.experiment_service import run_noise_sweep

router = APIRouter(prefix="/api/experiments", tags=["experiments"])


@router.post("", response_model=ExperimentOut, status_code=201)
def create_experiment(payload: ExperimentCreateRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    experiment = run_noise_sweep(
        db, user,
        experiment_name=payload.experiment_name,
        circuit_config=payload.circuit.model_dump(),
        shots=payload.shots,
        noise_levels=payload.noise_levels,
    )
    return experiment


@router.get("", response_model=list[ExperimentOut])
def list_experiments(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Experiment).filter(Experiment.user_id == user.id).order_by(Experiment.created_at.desc()).all()


@router.post("/{experiment_id}/run", response_model=ExperimentOut)
def rerun_experiment(experiment_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Re-execute an existing experiment's noise sweep with its stored configuration."""
    from fastapi import HTTPException, status

    experiment = db.get(Experiment, experiment_id)
    if experiment is None or experiment.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Experiment not found")

    cfg = experiment.experiment_config
    new_experiment = run_noise_sweep(
        db, user,
        experiment_name=f"{experiment.experiment_name} (rerun)",
        circuit_config=cfg["circuit"],
        shots=cfg["shots"],
        noise_levels=cfg["noise_levels"],
    )
    return new_experiment


@router.get("/{experiment_id}")
def get_experiment(experiment_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    experiment = db.get(Experiment, experiment_id)
    if experiment is None or experiment.user_id != user.id:
        from fastapi import HTTPException, status
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Experiment not found")
    return {
        "experiment": ExperimentOut.model_validate(experiment),
        "runs": [ExperimentRunOut.model_validate(r) for r in experiment.runs],
    }
