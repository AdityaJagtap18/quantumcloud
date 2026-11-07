"""FastAPI application entrypoint: CORS, rate limiting, router wiring,
and startup-time table creation + backend registry seeding.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import algorithms, auth, backends, circuits, dashboard, experiments, jobs
from app.core.config import settings
from app.db.session import Base, SessionLocal, engine
from app.services.backend_service import seed_backends
from app.services.rate_limit import rate_limit_dependency


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_backends(db)
    finally:
        db.close()
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name}


rate_limited = Depends(rate_limit_dependency)

app.include_router(auth.router, dependencies=[rate_limited])
app.include_router(backends.router, dependencies=[rate_limited])
app.include_router(circuits.router, dependencies=[rate_limited])
app.include_router(jobs.router, dependencies=[rate_limited])
app.include_router(experiments.router, dependencies=[rate_limited])
app.include_router(algorithms.router, dependencies=[rate_limited])
app.include_router(dashboard.router, dependencies=[rate_limited])
