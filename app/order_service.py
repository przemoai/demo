"""Order creation and retrieval. MongoDB is the source of truth for orders."""

import logging
from datetime import UTC, datetime
from uuid import uuid4

from motor.motor_asyncio import AsyncIOMotorDatabase
from redis.asyncio import Redis

from app.cart_service import clear_cart, get_cart
from app.errors import EmptyCartError
from app.models import Order, OrderItem

logger = logging.getLogger(__name__)


async def create_order(db: AsyncIOMotorDatabase, redis: Redis, user_id: str) -> Order:
    cart = await get_cart(redis, user_id)
    if not cart.items:
        raise EmptyCartError(user_id)

    order = Order(
        order_id=str(uuid4()),
        user_id=user_id,
        items=[
            OrderItem(
                product_id=item.product_id,
                name=item.name,
                price=item.price,
                quantity=item.quantity,
                subtotal=item.subtotal,
            )
            for item in cart.items
        ],
        total=cart.total,
        created_at=datetime.now(UTC),
    )
    await db.orders.insert_one(order.model_dump(mode="json"))
    logger.info(
        "order created: order_id=%s user=%s total=%s", order.order_id, user_id, order.total
    )

    await clear_cart(redis, user_id)
    return order


async def list_orders(db: AsyncIOMotorDatabase, user_id: str) -> list[Order]:
    cursor = db.orders.find({"user_id": user_id}, {"_id": 0}).sort("created_at", -1)
    documents = await cursor.to_list(length=None)
    return [Order.model_validate(doc) for doc in documents]
