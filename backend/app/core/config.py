"""Centralized application settings, loaded from environment variables.

Defaults target the Docker Compose stack (Postgres + Redis). For local
development without Docker, set DATABASE_URL to a sqlite URL and
REDIS_URL to "fakeredis://" to use an in-memory substitute (see
app/workers/queue.py) — this is what the test suite does.
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "QuantumCloud"
    environment: str = "development"

    database_url: str = "postgresql+psycopg2://quantumcloud:quantumcloud@postgres:5432/quantumcloud"
    redis_url: str = "redis://redis:6379/0"

    jwt_secret_key: str = "CHANGE_ME_IN_PRODUCTION"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24

    max_qubits_statevector: int = 20  # statevector memory grows as 2^n complex128 (16 bytes)
    max_qubits_shots: int = 30
    max_shots: int = 100_000
    job_execution_timeout_seconds: int = 60

    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    rate_limit_requests_per_minute: int = 120


settings = Settings()
