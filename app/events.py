"""Redis Pub/Sub broadcast of cart-change events between replicas.

Cart state itself always lives in Redis (see app.cart_service), so any
replica reading a cart is already consistent by construction. This module
adds a Pub/Sub channel on top so that a change made by one replica is
*actively broadcast to and observed by* every other replica in real time,
which is what this POC exists to demonstrate. Each replica subscribes on
startup and logs every event it receives, showing exactly when replica B
becomes aware of a change made on replica A.
"""

import asyncio
import json
import logging
from datetime import UTC, datetime

from redis.asyncio import Redis

from app.config import get_settings

CART_EVENTS_CHANNEL = "cart-events"

logger = logging.getLogger(__name__)


async def publish_cart_event(
    redis: Redis,
    *,
    event: str,
    user_id: str,
    product_id: str | None = None,
    quantity: int | None = None,
) -> None:
    settings = get_settings()
    payload = {
        "event": event,
        "user_id": user_id,
        "product_id": product_id,
        "quantity": quantity,
        "replica_id": settings.replica_id,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    await redis.publish(CART_EVENTS_CHANNEL, json.dumps(payload))
    logger.info("published cart event: %s", payload)


async def run_cart_event_subscriber(redis: Redis) -> None:
    """Log every cart event published by any replica, including this one.

    Runs as a background task for the lifetime of the app. Cancellation
    (on shutdown) is expected and handled by the caller.
    """
    settings = get_settings()
    pubsub = redis.pubsub()
    await pubsub.subscribe(CART_EVENTS_CHANNEL)
    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            payload = json.loads(message["data"])
            if payload.get("replica_id") == settings.replica_id:
                logger.info("consumed own cart event: %s", payload)
            else:
                logger.info("consumed cart event from peer replica: %s", payload)
    finally:
        await pubsub.unsubscribe(CART_EVENTS_CHANNEL)
        await pubsub.aclose()


def start_subscriber_task(redis: Redis) -> asyncio.Task[None]:
    return asyncio.create_task(run_cart_event_subscriber(redis))
