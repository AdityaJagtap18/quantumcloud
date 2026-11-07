"""Redis connection + RQ queue setup.

REDIS_URL == "fakeredis://" switches to an in-memory fakeredis
connection with a *synchronous* queue (jobs run immediately, in-process,
when enqueued) — used for local development without Docker and for the
test suite. Any other URL is treated as a real Redis connection with an
*asynchronous* queue, consumed by a separate `rq worker` process (see
app/workers/worker_main.py), which is how the Docker Compose stack runs.
"""
from __future__ import annotations

from functools import lru_cache

from rq import Queue

from app.core.config import settings

QUEUE_NAME = "quantum_jobs"


@lru_cache
def get_redis_connection():
    if settings.redis_url.startswith("fakeredis://"):
        import fakeredis

        return fakeredis.FakeStrictRedis()
    import redis

    return redis.Redis.from_url(settings.redis_url)


@lru_cache
def get_queue() -> Queue:
    is_fake = settings.redis_url.startswith("fakeredis://")
    return Queue(QUEUE_NAME, connection=get_redis_connection(), is_async=not is_fake)
