"""A minimal fixed-window rate limiter backed by the same Redis/fakeredis
connection the job queue uses — no extra infrastructure required.
"""
from __future__ import annotations

import time

from fastapi import HTTPException, Request, status

from app.core.config import settings
from app.workers.queue import get_redis_connection


def rate_limit_dependency(request: Request) -> None:
    conn = get_redis_connection()
    client_id = request.client.host if request.client else "unknown"
    window = int(time.time() // 60)
    key = f"ratelimit:{client_id}:{window}"

    count = conn.incr(key)
    if count == 1:
        conn.expire(key, 60)

    if count > settings.rate_limit_requests_per_minute:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Rate limit exceeded. Try again shortly.")
