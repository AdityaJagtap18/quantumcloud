from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.algorithms.library import ALGORITHMS, get_algorithm_circuit_json, list_algorithms
from app.models.models import User
from app.schemas.schemas import AlgorithmOut
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/algorithms", tags=["algorithms"])


@router.get("", response_model=list[AlgorithmOut])
def get_algorithms():
    return list_algorithms()


@router.get("/{algorithm_id}", response_model=AlgorithmOut)
def get_algorithm(algorithm_id: str):
    if algorithm_id not in ALGORITHMS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Algorithm not found")
    return next(a for a in list_algorithms() if a["id"] == algorithm_id)


@router.post("/{algorithm_id}/load")
def load_algorithm(algorithm_id: str, user: User = Depends(get_current_user)):
    """Return the algorithm's circuit in this project's JSON format, ready
    to load into the circuit editor or submit directly as a job."""
    if algorithm_id not in ALGORITHMS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Algorithm not found")
    return {"circuit": get_algorithm_circuit_json(algorithm_id)}
