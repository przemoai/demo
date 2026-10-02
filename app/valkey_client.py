"""Valkey connection lifecycle.

Valkey is the single source of truth for cart state: every cart read hits
Valkey directly, so any replica always sees the latest cart regardless of
which replica last wrote to it. Valkey Pub/Sub is used on top of that to
broadcast cart-change events between replicas for observability (see
app.events) — it is not required for read consistency, but it makes the
"replica A changed something, replica B knows about it" behavior explicit
and demonstrable, per the architecture this POC targets.

The `REDIS_URL` setting/env var name is kept as-is (see app.config) for
backward compatibility: valkey-py's `from_url` natively accepts the
`redis://` scheme (Valkey is wire- and protocol-compatible with Redis),
so no connection-string changes are required by this migration.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from valkey.asyncio import Valkey

from app.config import get_settings


@asynccontextmanager
async def valkey_lifespan() -> AsyncIterator[Valkey]:
    settings = get_settings()
    client: Valkey = Valkey.from_url(settings.redis_url, decode_responses=True)
    try:
        await client.ping()
        yield client
    finally:
        await client.aclose()
