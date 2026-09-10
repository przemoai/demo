from typing import Annotated

from fastapi import APIRouter, Depends
from redis.asyncio import Redis

from app import cart_service
from app.dependencies import get_redis
from app.models import AddCartItemRequest, Cart

router = APIRouter(prefix="/cart", tags=["cart"])


@router.get("/{user_id}", response_model=Cart)
async def get_cart(user_id: str, redis: Annotated[Redis, Depends(get_redis)]) -> Cart:
    return await cart_service.get_cart(redis, user_id)


@router.post("/{user_id}/items", response_model=Cart)
async def add_item(
    user_id: str, body: AddCartItemRequest, redis: Annotated[Redis, Depends(get_redis)]
) -> Cart:
    return await cart_service.add_item(redis, user_id, body.product_id, body.quantity)


@router.delete("/{user_id}/items/{product_id}", response_model=Cart)
async def remove_item(
    user_id: str, product_id: str, redis: Annotated[Redis, Depends(get_redis)]
) -> Cart:
    return await cart_service.remove_item(redis, user_id, product_id)
