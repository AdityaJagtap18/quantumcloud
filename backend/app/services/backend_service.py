"""Seed and list the quantum_backends table from the in-code BACKEND_REGISTRY
(app/quantum/engine.py), so the DB row IDs line up with what the engine
actually supports."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.models import QuantumBackend
from app.quantum.engine import BACKEND_REGISTRY


def seed_backends(db: Session) -> None:
    for backend_type, info in BACKEND_REGISTRY.items():
        existing = db.query(QuantumBackend).filter(QuantumBackend.name == info["name"]).first()
        if existing is None:
            db.add(QuantumBackend(
                name=info["name"],
                backend_type=backend_type,
                configuration={"description": info["description"]},
                is_active=True,
            ))
    db.commit()


def list_active_backends(db: Session) -> list[QuantumBackend]:
    return db.query(QuantumBackend).filter(QuantumBackend.is_active.is_(True)).all()
