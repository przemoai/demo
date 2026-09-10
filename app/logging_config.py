"""Minimal structured logging, tagged with the replica identity.

Every log line includes which replica emitted it, so replica behavior
(who handled a request, who published/consumed a cart event) is visible
in `docker compose logs` without extra tooling.
"""

import logging

from app.config import get_settings


class ReplicaFilter(logging.Filter):
    def __init__(self, replica_id: str) -> None:
        super().__init__()
        self._replica_id = replica_id

    def filter(self, record: logging.LogRecord) -> bool:
        record.replica_id = self._replica_id
        return True


def configure_logging() -> None:
    settings = get_settings()

    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)-8s [replica=%(replica_id)s] %(name)s: %(message)s"
        )
    )
    handler.addFilter(ReplicaFilter(settings.replica_id))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(settings.log_level.upper())
