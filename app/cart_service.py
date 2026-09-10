"""Cart operations. Redis is read and written directly on every call —
no in-memory or per-replica state is kept, so any replica always reflects
the latest cart regardless of which replica last modified it.
"""

import logging

from redis.asyncio import Redis

from app.events import publish_cart_event
from app.models import Cart, CartItem
from app.product_service import get_product

logger = logging.getLogger(__name__)


def _cart_key(user_id: str) -> str:
    return f"cart:{user_id}"


async def _raw_cart(redis: Redis, user_id: str) -> dict[str, int]:
    raw = await redis.hgetall(_cart_key(user_id))  # type: ignore[misc]
    return {product_id: int(quantity) for product_id, quantity in raw.items()}


async def get_cart(redis: Redis, user_id: str) -> Cart:
    raw = await _raw_cart(redis, user_id)
    items = []
    total = 0.0
    for product_id, quantity in raw.items():
        product = get_product(product_id)
        subtotal = round(product.price * quantity, 2)
        items.append(
            CartItem(
                product_id=product_id,
                name=product.name,
                price=product.price,
                quantity=quantity,
                subtotal=subtotal,
            )
        )
        total += subtotal
    return Cart(user_id=user_id, items=items, total=round(total, 2))


async def add_item(redis: Redis, user_id: str, product_id: str, quantity: int) -> Cart:
    get_product(product_id)  # fail fast on unknown product before writing state
    await redis.hincrby(_cart_key(user_id), product_id, quantity)  # type: ignore[misc]
    logger.info("cart updated: user=%s added product=%s qty=%s", user_id, product_id, quantity)
    await publish_cart_event(
        redis, event="item_added", user_id=user_id, product_id=product_id, quantity=quantity
    )
    return await get_cart(redis, user_id)


async def remove_item(redis: Redis, user_id: str, product_id: str) -> Cart:
    await redis.hdel(_cart_key(user_id), product_id)  # type: ignore[misc]
    logger.info("cart updated: user=%s removed product=%s", user_id, product_id)
    await publish_cart_event(redis, event="item_removed", user_id=user_id, product_id=product_id)
    return await get_cart(redis, user_id)


async def clear_cart(redis: Redis, user_id: str) -> None:
    await redis.delete(_cart_key(user_id))
    logger.info("cart cleared: user=%s", user_id)
    await publish_cart_event(redis, event="cart_cleared", user_id=user_id)
