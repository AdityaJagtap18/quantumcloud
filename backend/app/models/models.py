"""SQLAlchemy ORM models for QuantumCloud's core tables."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class JobStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    VALIDATING = "VALIDATING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    jobs: Mapped[list["QuantumJob"]] = relationship(back_populates="user")
    experiments: Mapped[list["Experiment"]] = relationship(back_populates="user")


class QuantumBackend(Base):
    __tablename__ = "quantum_backends"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    backend_type: Mapped[str] = mapped_column(String, nullable=False)  # ideal_qasm | statevector | noisy | custom_noise
    configuration: Mapped[dict] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class QuantumJob(Base):
    __tablename__ = "quantum_jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid, index=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), index=True)
    backend_id: Mapped[str] = mapped_column(String, ForeignKey("quantum_backends.id"))
    circuit_config: Mapped[dict] = mapped_column(JSON, nullable=False)
    shots: Mapped[int] = mapped_column(Integer, default=1024)
    noise_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.QUEUED, index=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    execution_time: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship(back_populates="jobs")
    backend: Mapped["QuantumBackend"] = relationship()
    result: Mapped["QuantumResult"] = relationship(back_populates="job", uselist=False)


class QuantumResult(Base):
    __tablename__ = "quantum_results"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    job_id: Mapped[str] = mapped_column(String, ForeignKey("quantum_jobs.id"), unique=True, index=True)
    measurement_counts: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    probabilities: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    statevector: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # {"real": [...], "imag": [...]}, size-limited
    execution_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    job: Mapped["QuantumJob"] = relationship(back_populates="result")


class Experiment(Base):
    __tablename__ = "experiments"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), index=True)
    experiment_name: Mapped[str] = mapped_column(String, nullable=False)
    experiment_config: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="experiments")
    runs: Mapped[list["ExperimentRun"]] = relationship(back_populates="experiment")


class ExperimentRun(Base):
    __tablename__ = "experiment_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    experiment_id: Mapped[str] = mapped_column(String, ForeignKey("experiments.id"), index=True)
    noise_level: Mapped[float] = mapped_column(Float, nullable=False)
    job_id: Mapped[str | None] = mapped_column(String, ForeignKey("quantum_jobs.id"), nullable=True)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    experiment: Mapped["Experiment"] = relationship(back_populates="runs")
