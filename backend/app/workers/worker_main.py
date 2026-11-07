"""Entrypoint for the Docker Compose `worker` service: a long-running RQ
worker consuming the quantum_jobs queue against the real Redis instance.
Run with: `python -m app.workers.worker_main`.
"""
from __future__ import annotations

import logging

from rq import Worker

from app.workers.queue import QUEUE_NAME, get_redis_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def main() -> None:
    worker = Worker([QUEUE_NAME], connection=get_redis_connection())
    worker.work()


if __name__ == "__main__":
    main()
