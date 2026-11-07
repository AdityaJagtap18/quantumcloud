from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import QuantumBackend
from app.quantum.engine import BACKEND_REGISTRY
from app.schemas.schemas import BackendOut

router = APIRouter(prefix="/api/backends", tags=["backends"])


def _to_out(backend: QuantumBackend) -> BackendOut:
    info = BACKEND_REGISTRY.get(backend.backend_type, {})
    return BackendOut(
        id=backend.id,
        name=backend.name,
        backend_type=backend.backend_type,
        description=info.get("description", ""),
        requires_measurements=info.get("requires_measurements", True),
    )


@router.get("", response_model=list[BackendOut])
def get_backends(db: Session = Depends(get_db)):
    backends = db.query(QuantumBackend).filter(QuantumBackend.is_active.is_(True)).all()
    return [_to_out(b) for b in backends]


@router.get("/{backend_id}", response_model=BackendOut)
def get_backend(backend_id: str, db: Session = Depends(get_db)):
    backend = db.get(QuantumBackend, backend_id)
    if backend is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Backend not found")
    return _to_out(backend)
