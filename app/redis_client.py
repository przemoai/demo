"""Redis connection lifecycle.

Redis is the single source of truth for cart state: every cart read hits
Redis directly, so any replica always sees the latest cart regardless of
which replica last wrote to it. Redis Pub/Sub is used on top of that to
broadcast cart-change events between replicas for observability (see
app.events) — it is not required for read consistency, but it makes the
"replica A changed something, replica B knows about it" behavior explicit
and demonstrable, per the architecture this POC targets.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from redis.asyncio import Redis

from app.config import get_settings


@asynccontextmanager
async def redis_lifespan() -> AsyncIterator[Redis]:
    settings = get_settings()
    client: Redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        await client.ping()
        yield client
    finally:
        await client.aclose()
