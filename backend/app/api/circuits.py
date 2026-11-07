from __future__ import annotations

from fastapi import APIRouter, Depends

from app.models.models import User
from app.schemas.schemas import (
    CircuitAnalyzeRequest,
    CircuitTranspileRequest,
    CircuitValidateRequest,
    CircuitValidateResponse,
)
from app.services.auth_service import get_current_user
from app.services.circuit_service import analyze, transpile_report, validate

router = APIRouter(prefix="/api/circuits", tags=["circuits"])


@router.post("/validate", response_model=CircuitValidateResponse)
def validate_circuit(payload: CircuitValidateRequest, user: User = Depends(get_current_user)):
    return validate(payload.circuit.model_dump())


@router.post("/analyze")
def analyze_circuit(payload: CircuitAnalyzeRequest, user: User = Depends(get_current_user)):
    return analyze(payload.circuit.model_dump(), payload.topology)


@router.post("/transpile")
def transpile_circuit(payload: CircuitTranspileRequest, user: User = Depends(get_current_user)):
    return transpile_report(payload.circuit.model_dump(), payload.topology, payload.optimization_level)
