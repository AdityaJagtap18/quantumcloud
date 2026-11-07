"""Pydantic request/response models for the API layer."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field


# --- Auth -------------------------------------------------------------------
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


# --- Backends -----------------------------------------------------------------
class BackendOut(BaseModel):
    id: str
    name: str
    backend_type: str
    description: str
    requires_measurements: bool


# --- Circuits -----------------------------------------------------------------
class CircuitOperation(BaseModel):
    gate: str
    qubits: list[int]
    clbits: list[int] | None = None
    params: list[float] | None = None
    condition: dict[str, int] | None = None


class CircuitConfig(BaseModel):
    num_qubits: int
    num_clbits: int
    operations: list[dict[str, Any]]


class CircuitValidateRequest(BaseModel):
    circuit: CircuitConfig


class CircuitValidateResponse(BaseModel):
    valid: bool
    error: str | None = None


class CircuitAnalyzeRequest(BaseModel):
    circuit: CircuitConfig
    topology: str = "fully_connected"


class CircuitTranspileRequest(BaseModel):
    circuit: CircuitConfig
    topology: str = "fully_connected"
    optimization_level: int = 1


# --- Jobs -----------------------------------------------------------------
class JobCreateRequest(BaseModel):
    circuit: CircuitConfig
    backend_id: str
    shots: int = 1024
    noise_config: dict[str, Any] | None = None


class JobOut(BaseModel):
    id: str
    user_id: str
    backend_id: str
    circuit_config: dict[str, Any]
    shots: int
    noise_config: dict[str, Any] | None
    status: str
    submitted_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    execution_time: float | None
    error_message: str | None

    class Config:
        from_attributes = True


class JobResultOut(BaseModel):
    job_id: str
    measurement_counts: dict[str, int] | None
    probabilities: dict[str, float] | None
    statevector: dict[str, list[float]] | None
    execution_metadata: dict[str, Any]

    class Config:
        from_attributes = True


# --- Experiments -----------------------------------------------------------------
class ExperimentCreateRequest(BaseModel):
    experiment_name: str
    circuit: CircuitConfig
    backend_id: str
    shots: int = 1024
    noise_levels: list[float]
    reference_statevector: dict[str, list[float]] | None = None


class ExperimentOut(BaseModel):
    id: str
    experiment_name: str
    experiment_config: dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


class ExperimentRunOut(BaseModel):
    id: str
    noise_level: float
    job_id: str | None
    metrics: dict[str, Any]

    class Config:
        from_attributes = True


# --- Algorithms -----------------------------------------------------------------
class AlgorithmOut(BaseModel):
    id: str
    name: str
    description: str
    math_intuition: str
    expected_distribution: dict[str, float] | None
