"""Cross-replica synchronization tests.

This is the most important test module in the POC: it proves that a cart
change made through one API replica is immediately visible through the
other, and that the Redis Pub/Sub channel described in the architecture is
actually carrying the corresponding event.
"""

import asyncio
import json
import os

import pytest
from httpx import AsyncClient
from redis.asyncio import Redis

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")


@pytest.mark.asyncio
async def test_cart_added_on_replica1_is_visible_on_replica2(
    replica1: AsyncClient, replica2: AsyncClient, user_id: str
) -> None:
    add_response = await replica1.post(
        f"/cart/{user_id}/items", json={"product_id": "p1", "quantity": 2}
    )
    assert add_response.status_code == 200
    assert add_response.headers["x-replica-id"] == "replica-1"

    read_response = await replica2.get(f"/cart/{user_id}")
    assert read_response.status_code == 200
    assert read_response.headers["x-replica-id"] == "replica-2"

    cart = read_response.json()
    assert cart["items"] == [
        {
            "product_id": "p1",
            "name": "Mechanical Keyboard",
            "price": 89.99,
            "quantity": 2,
            "subtotal": 179.98,
        }
    ]


@pytest.mark.asyncio
async def test_cart_updated_on_replica2_is_visible_on_replica1(
    replica1: AsyncClient, replica2: AsyncClient, user_id: str
) -> None:
    await replica2.post(f"/cart/{user_id}/items", json={"product_id": "p4", "quantity": 1})

    read_response = await replica1.get(f"/cart/{user_id}")
    assert read_response.status_code == 200
    product_ids = [item["product_id"] for item in read_response.json()["items"]]
    assert "p4" in product_ids


@pytest.mark.asyncio
async def test_order_created_via_replica2_persists_cart_contents_added_via_replica1(
    replica1: AsyncClient, replica2: AsyncClient, user_id: str
) -> None:
    await replica1.post(f"/cart/{user_id}/items", json={"product_id": "p5", "quantity": 4})

    order_response = await replica2.post("/orders", json={"user_id": user_id})
    assert order_response.status_code == 201
    order = order_response.json()
    assert order["items"] == [
        {
            "product_id": "p5",
            "name": "Laptop Stand",
            "price": 24.99,
            "quantity": 4,
            "subtotal": 99.96,
        }
    ]

    # Cart clearing propagates too: replica1 must see the empty cart.
    cart_response = await replica1.get(f"/cart/{user_id}")
    assert cart_response.json()["items"] == []


@pytest.mark.asyncio
async def test_replicas_handle_requests_independently(
    replica1: AsyncClient, replica2: AsyncClient
) -> None:
    health1, health2 = await asyncio.gather(replica1.get("/health"), replica2.get("/health"))
    assert health1.json() == {"status": "ok", "replica_id": "replica-1"}
    assert health2.json() == {"status": "ok", "replica_id": "replica-2"}


@pytest.mark.asyncio
async def test_cart_change_is_broadcast_on_the_pubsub_channel(
    replica1: AsyncClient, user_id: str
) -> None:
    """Directly observe the Redis Pub/Sub event described in the README."""
    redis: Redis = Redis.from_url(REDIS_URL, decode_responses=True)
    pubsub = redis.pubsub()
    await pubsub.subscribe("cart-events")
    try:
        await replica1.post(
            f"/cart/{user_id}/items", json={"product_id": "p2", "quantity": 1}
        )

        event = None
        async with asyncio.timeout(5):
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                payload = json.loads(message["data"])
                if payload["user_id"] == user_id:
                    event = payload
                    break

        assert event is not None
        assert event["event"] == "item_added"
        assert event["product_id"] == "p2"
        assert event["replica_id"] == "replica-1"
    finally:
        await pubsub.unsubscribe("cart-events")
        await pubsub.aclose()
        await redis.aclose()
